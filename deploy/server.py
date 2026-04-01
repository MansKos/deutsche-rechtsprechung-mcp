"""
Hosted MCP server for German court decisions.

Runs as HTTP endpoint for use with Claude Desktop (HTTP connector),
Cowork, and any other MCP client that supports remote servers.
"""

import os
import json
import sqlite3
from mcp.server.fastmcp import FastMCP

DATA_DIR = os.environ.get("RECHTSPRECHUNG_DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "decisions.db")
PORT = int(os.environ.get("PORT", 8002))

mcp = FastMCP(
    "deutsche-rechtsprechung",
    stateless_http=True,
    host="0.0.0.0",
    port=PORT,
)


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _search(query: str, limit: int = 10) -> list[dict]:
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


def _get_by_doknr(doknr: str) -> dict | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM decisions WHERE doknr = ?", (doknr,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


@mcp.tool()
def search_decisions(query: str, limit: int = 10) -> str:
    """Durchsucht deutsche Gerichtsentscheidungen nach Text, Aktenzeichen oder Normen.

    Args:
        query: Suchanfrage (z.B. 'Insolvenzverfahren', 'BGH IX ZB 72/08', '§ 823 BGB').
        limit: Anzahl der Ergebnisse (Standard: 10).
    """
    try:
        results = _search(query, limit)
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
    try:
        result = _get_by_doknr(doknr)
        if result is None:
            return f"Keine Entscheidung gefunden mit DokNr: {doknr}"
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Fehler beim Abruf: {e}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
