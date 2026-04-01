"""
MCP Server for the Claude Desktop Extension.

This is a self-contained server for the .mcpb desktop extension.
It uses stdio transport and automatically downloads the database on first use.
"""

import os
import sys
import json
import sqlite3
import urllib.request
import zipfile
import tempfile
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _get_data_dir() -> str:
    env_path = os.environ.get("RECHTSPRECHUNG_DATA_DIR")
    if env_path:
        return env_path
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(base, "deutsche-rechtsprechung")


def _get_db_path() -> str:
    env_path = os.environ.get("SQLITE_DB_PATH")
    if env_path:
        return env_path
    return os.path.join(_get_data_dir(), "decisions.db")


# ---------------------------------------------------------------------------
# Database download
# ---------------------------------------------------------------------------

DB_URL = os.environ.get(
    "RECHTSPRECHUNG_DB_URL",
    "https://github.com/MansKos/deutsche-rechtsprechung-mcp/releases/download/v0.1.0/decisions.db.zip",
)


def _download_db(url: str, dest_path: str) -> None:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    print(f"Downloading database from {url}...", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = os.path.join(tmp_dir, "db.zip")

        def _progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded * 100 // total_size)
                print(f"\r  Progress: {pct}%", end="", file=sys.stderr)

        urllib.request.urlretrieve(url, zip_path, reporthook=_progress)
        print("", file=sys.stderr)

        with zipfile.ZipFile(zip_path, "r") as zf:
            db_files = [n for n in zf.namelist() if n.endswith(".db")]
            if not db_files:
                raise RuntimeError("ZIP contains no .db file")
            zf.extract(db_files[0], tmp_dir)
            os.replace(os.path.join(tmp_dir, db_files[0]), dest_path)

    print(f"Database ready: {dest_path}", file=sys.stderr)


def _ensure_db() -> str:
    db_path = _get_db_path()
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
            conn.close()
            if count > 0:
                return db_path
        except Exception:
            pass
        os.remove(db_path)

    _download_db(DB_URL, db_path)
    return db_path


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SQLiteSearch:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def search(self, query: str, limit: int = 10) -> list[dict]:
        conn = self._connect()
        try:
            fts_query = query
            fts_operators = {'"', "AND", "OR", "NOT", "NEAR", "*"}
            if not any(op in query for op in fts_operators):
                words = query.split()
                if len(words) > 1:
                    fts_query = " ".join(f'"{w}"' for w in words)

            rows = conn.execute(
                """
                SELECT d.*, fts.rank AS score,
                       snippet(decisions_fts, 2, '<b>', '</b>', '...', 40) AS snippet
                FROM decisions_fts fts
                JOIN decisions d ON d.rowid = fts.rowid
                WHERE decisions_fts MATCH ?
                ORDER BY fts.rank LIMIT ?
                """,
                (fts_query, limit),
            ).fetchall()

            return [
                {
                    "title": r["title"], "az": r["az"], "gericht": r["gericht"],
                    "normen": r["normen"], "doknr": r["doknr"], "date": r["datum"],
                    "score": r["score"], "snippet": r["snippet"] or "",
                }
                for r in rows
            ]
        except Exception:
            like = f"%{query}%"
            rows = conn.execute(
                "SELECT * FROM decisions WHERE title LIKE ? OR full_text LIKE ? OR az LIKE ? LIMIT ?",
                (like, like, like, limit),
            ).fetchall()
            return [
                {
                    "title": r["title"], "az": r["az"], "gericht": r["gericht"],
                    "normen": r["normen"], "doknr": r["doknr"], "date": r["datum"],
                    "score": 0, "snippet": (r["full_text"] or "")[:200] + "...",
                }
                for r in rows
            ]
        finally:
            conn.close()

    def get_by_doknr(self, doknr: str) -> dict | None:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM decisions WHERE doknr = ?", (doknr,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("deutsche-rechtsprechung")
_search = None


def _get_search() -> SQLiteSearch:
    global _search
    if _search is None:
        db_path = _ensure_db()
        _search = SQLiteSearch(db_path)
    return _search


@mcp.tool()
def search_decisions(query: str, limit: int = 10) -> str:
    """Durchsucht deutsche Gerichtsentscheidungen nach Text, Aktenzeichen oder Normen.

    Args:
        query: Suchanfrage (z.B. 'Insolvenzverfahren', 'BGH IX ZB 72/08', '§ 823 BGB').
        limit: Anzahl der Ergebnisse (Standard: 10).
    """
    try:
        results = _get_search().search(query, limit)
        if not results:
            return "Keine Ergebnisse gefunden."
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Fehler bei der Suche: {str(e)}"


@mcp.tool()
def get_decision_by_doknr(doknr: str) -> str:
    """Ruft den Volltext einer Gerichtsentscheidung anhand der Dokumentennummer (DokNr) ab.

    Args:
        doknr: Die Dokumentennummer (z.B. 'KARE600052872').
    """
    try:
        result = _get_search().get_by_doknr(doknr)
        if result is None:
            return f"Keine Entscheidung gefunden mit DokNr: {doknr}"
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Fehler beim Abruf: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
