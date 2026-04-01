import json
from mcp.server.fastmcp import FastMCP
from search_backend import create_backend

# Initialize FastMCP
mcp = FastMCP("court-decisions-mcp", stateless_http=True, host='0.0.0.0', port=8002, debug=True)

# Initialize search backend (SQLite or OpenSearch, based on SEARCH_BACKEND env var)
backend = create_backend()

@mcp.tool()
def search_decisions(query: str, limit: int = 10) -> str:
    """Search for German court decisions by text or metadata.

    Args:
        query: The search query (e.g. 'Insolvenzverfahren', 'BGH IX ZB 72/08').
        limit: Number of results to return (default 10).
    """
    try:
        results = backend.search(query, limit)
        if not results:
            return "No results found."
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error searching: {str(e)}"

@mcp.tool()
def get_decision_by_doknr(doknr: str) -> str:
    """Get the full text of a court decision by its document number (DokNr).

    Args:
        doknr: The document number (e.g. 'KARE600052872').
    """
    try:
        result = backend.get_by_doknr(doknr)
        if result is None:
            return f"No decision found with DokNr: {doknr}"
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error retrieving decision: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
