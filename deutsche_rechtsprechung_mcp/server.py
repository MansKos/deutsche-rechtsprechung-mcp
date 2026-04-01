"""
MCP Server for German court decisions.

Transports:
  - stdio (default): For Claude Desktop, MCPB, and local use
  - streamable-http: For Docker / remote deployment

Set MCP_TRANSPORT=streamable-http to switch to HTTP mode.
"""

import os
import sys
import json
from mcp.server.fastmcp import FastMCP
from deutsche_rechtsprechung_mcp.search_backend import create_backend
from deutsche_rechtsprechung_mcp.db_setup import ensure_database

# Determine transport before creating the server
transport = os.environ.get("MCP_TRANSPORT", "stdio")
server_kwargs = {"name": "deutsche-rechtsprechung"}
if transport == "streamable-http":
    server_kwargs.update(stateless_http=True, host="0.0.0.0", port=8002)

mcp = FastMCP(**server_kwargs)


def _get_backend():
    """Lazy-init backend so the DB is set up before first query."""
    global _backend
    if _backend is None:
        ensure_database()
        _backend = create_backend()
    return _backend


_backend = None


@mcp.tool()
def search_decisions(query: str, limit: int = 10) -> str:
    """Durchsucht deutsche Gerichtsentscheidungen nach Text, Aktenzeichen oder Normen.

    Args:
        query: Suchanfrage (z.B. 'Insolvenzverfahren', 'BGH IX ZB 72/08', '§ 823 BGB').
        limit: Anzahl der Ergebnisse (Standard: 10).
    """
    try:
        backend = _get_backend()
        results = backend.search(query, limit)
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
        backend = _get_backend()
        result = backend.get_by_doknr(doknr)
        if result is None:
            return f"Keine Entscheidung gefunden mit DokNr: {doknr}"
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Fehler beim Abruf: {str(e)}"


def main():
    """Entry point for the MCP server."""
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
