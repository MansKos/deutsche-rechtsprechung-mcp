"""
Self-contained MCP server for the Claude Code Plugin.

Uses stdio transport. Downloads the SQLite database automatically on first use.
All data is stored in ${CLAUDE_PLUGIN_DATA} (persistent across plugin updates).
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
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = os.environ.get("RECHTSPRECHUNG_DATA_DIR", os.path.expanduser("~/.local/share/deutsche-rechtsprechung"))
DB_PATH = os.path.join(DATA_DIR, "decisions.db")
DB_URL = os.environ.get(
    "RECHTSPRECHUNG_DB_URL",
    "https://github.com/MansKos/deutsche-rechtsprechung-mcp/releases/download/v0.1.0/decisions.db.zip",
) or "https://github.com/MansKos/deutsche-rechtsprechung-mcp/releases/download/v0.1.0/decisions.db.zip"

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def download_db():
    """Download and extract the pre-built database."""
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Lade Datenbank herunter: {DB_URL}", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "db.zip")

        def progress(block, block_size, total):
            if total > 0:
                pct = min(100, block * block_size * 100 // total)
                print(f"\r  {pct}%", end="", file=sys.stderr)

        urllib.request.urlretrieve(DB_URL, zip_path, reporthook=progress)
        print("", file=sys.stderr)

        with zipfile.ZipFile(zip_path, "r") as zf:
            db_files = [n for n in zf.namelist() if n.endswith(".db")]
            if not db_files:
                raise RuntimeError("ZIP enthält keine .db-Datei")
            zf.extract(db_files[0], tmp)
            os.replace(os.path.join(tmp, db_files[0]), DB_PATH)

    print(f"Datenbank bereit: {DB_PATH}", file=sys.stderr)


def ensure_db():
    """Make sure the database exists and is valid."""
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
            conn.close()
            if count > 0:
                return
        except Exception:
            pass
        os.remove(DB_PATH)
    download_db()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def search(query: str, limit: int = 10) -> list[dict]:
    conn = connect()
    try:
        fts_query = query
        fts_ops = {'"', "AND", "OR", "NOT", "NEAR", "*"}
        if not any(op in query for op in fts_ops):
            words = query.split()
            if len(words) > 1:
                fts_query = " ".join(f'"{w}"' for w in words)

        rows = conn.execute("""
            SELECT d.*, fts.rank AS score,
                   snippet(decisions_fts, 2, '<b>', '</b>', '...', 40) AS snippet
            FROM decisions_fts fts
            JOIN decisions d ON d.rowid = fts.rowid
            WHERE decisions_fts MATCH ?
            ORDER BY fts.rank LIMIT ?
        """, (fts_query, limit)).fetchall()

        return [{
            "title": r["title"], "az": r["az"], "gericht": r["gericht"],
            "normen": r["normen"], "doknr": r["doknr"], "date": r["datum"],
            "score": r["score"], "snippet": r["snippet"] or "",
        } for r in rows]
    except Exception:
        like = f"%{query}%"
        rows = conn.execute(
            "SELECT * FROM decisions WHERE title LIKE ? OR full_text LIKE ? OR az LIKE ? LIMIT ?",
            (like, like, like, limit),
        ).fetchall()
        return [{
            "title": r["title"], "az": r["az"], "gericht": r["gericht"],
            "normen": r["normen"], "doknr": r["doknr"], "date": r["datum"],
            "score": 0, "snippet": (r["full_text"] or "")[:200] + "...",
        } for r in rows]
    finally:
        conn.close()


def get_by_doknr(doknr: str) -> dict | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM decisions WHERE doknr = ?", (doknr,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("deutsche-rechtsprechung")
_db_ready = False


def _ensure():
    global _db_ready
    if not _db_ready:
        ensure_db()
        _db_ready = True


@mcp.tool()
def search_decisions(query: str, limit: int = 10) -> str:
    """Durchsucht deutsche Gerichtsentscheidungen nach Text, Aktenzeichen oder Normen.

    Args:
        query: Suchanfrage (z.B. 'Insolvenzverfahren', 'BGH IX ZB 72/08', '§ 823 BGB').
        limit: Anzahl der Ergebnisse (Standard: 10).
    """
    _ensure()
    try:
        results = search(query, limit)
        if not results:
            return "Keine Ergebnisse gefunden."
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Fehler bei der Suche: {e}"


@mcp.tool()
def get_decision_by_doknr(doknr: str) -> str:
    """Ruft den Volltext einer Gerichtsentscheidung anhand der Dokumentennummer (DokNr) ab.

    Args:
        doknr: Die Dokumentennummer (z.B. 'KARE600052872').
    """
    _ensure()
    try:
        result = get_by_doknr(doknr)
        if result is None:
            return f"Keine Entscheidung gefunden mit DokNr: {doknr}"
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Fehler beim Abruf: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
