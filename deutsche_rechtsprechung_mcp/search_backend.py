"""
Search backend abstraction.

Supports two backends:
- "sqlite" (default): Lightweight, uses SQLite FTS5, no external services needed
- "opensearch": Requires a running OpenSearch instance

Set SEARCH_BACKEND env var to choose.
"""

import os
import json
import sqlite3
from abc import ABC, abstractmethod
from deutsche_rechtsprechung_mcp.paths import get_db_path


class SearchBackend(ABC):
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[dict]:
        ...

    @abstractmethod
    def get_by_doknr(self, doknr: str) -> dict | None:
        ...


class SQLiteBackend(SearchBackend):
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or get_db_path()

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

            sql = """
                SELECT
                    d.*,
                    fts.rank AS score,
                    snippet(decisions_fts, 2, '<b>', '</b>', '...', 40) AS snippet
                FROM decisions_fts fts
                JOIN decisions d ON d.rowid = fts.rowid
                WHERE decisions_fts MATCH ?
                ORDER BY fts.rank
                LIMIT ?
            """
            rows = conn.execute(sql, (fts_query, limit)).fetchall()

            results = []
            for row in rows:
                results.append({
                    "title": row["title"],
                    "az": row["az"],
                    "gericht": row["gericht"],
                    "normen": row["normen"],
                    "doknr": row["doknr"],
                    "date": row["datum"],
                    "score": row["score"],
                    "snippet": row["snippet"] or "",
                })
            return results
        except Exception:
            like_pattern = f"%{query}%"
            sql = """
                SELECT * FROM decisions
                WHERE title LIKE ? OR full_text LIKE ? OR az LIKE ? OR normen LIKE ? OR doknr LIKE ?
                LIMIT ?
            """
            rows = conn.execute(
                sql, (like_pattern, like_pattern, like_pattern, like_pattern, like_pattern, limit)
            ).fetchall()
            return [
                {
                    "title": row["title"],
                    "az": row["az"],
                    "gericht": row["gericht"],
                    "normen": row["normen"],
                    "doknr": row["doknr"],
                    "date": row["datum"],
                    "score": 0,
                    "snippet": (row["full_text"] or "")[:200] + "...",
                }
                for row in rows
            ]
        finally:
            conn.close()

    def get_by_doknr(self, doknr: str) -> dict | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM decisions WHERE doknr = ?", (doknr,)
            ).fetchone()
            if row is None:
                return None
            return dict(row)
        finally:
            conn.close()


class OpenSearchBackend(SearchBackend):
    def __init__(self):
        from opensearchpy import OpenSearch

        self.host = os.environ.get("OPENSEARCH_HOST", "localhost")
        self.port = int(os.environ.get("OPENSEARCH_PORT", 9200))
        self.user = os.environ.get("OPENSEARCH_USER", "admin")
        self.password = os.environ.get("OPENSEARCH_PASSWORD", "ComplexPassword123!")
        self.index = "court-decisions"
        self.client = OpenSearch(
            hosts=[{"host": self.host, "port": self.port, "scheme": "https"}],
            http_compress=True,
            http_auth=(self.user, self.password),
            use_ssl=True,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
        )

    def search(self, query: str, limit: int = 10) -> list[dict]:
        search_body = {
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^2", "leitsatz^2", "full_text",
                        "az", "doknr", "normen",
                    ],
                }
            },
            "highlight": {"fields": {"full_text": {}}},
        }
        response = self.client.search(index=self.index, body=search_body)
        hits = response["hits"]["hits"]

        results = []
        for hit in hits:
            source = hit["_source"]
            snippet = ""
            if "highlight" in hit and "full_text" in hit["highlight"]:
                snippet = "... " + " ... ".join(hit["highlight"]["full_text"]) + " ..."
            else:
                snippet = (source.get("full_text") or "")[:200] + "..."

            results.append({
                "title": source.get("title", "No Title"),
                "az": source.get("az", "N/A"),
                "gericht": source.get("gericht", "N/A"),
                "normen": source.get("normen", "N/A"),
                "doknr": source.get("doknr", "N/A"),
                "date": source.get("datum", "N/A"),
                "score": hit["_score"],
                "snippet": snippet,
            })
        return results

    def get_by_doknr(self, doknr: str) -> dict | None:
        search_body = {"query": {"term": {"doknr": doknr}}}
        response = self.client.search(index=self.index, body=search_body)
        hits = response["hits"]["hits"]
        if not hits:
            return None
        return hits[0]["_source"]


def create_backend() -> SearchBackend:
    """Create the search backend based on the SEARCH_BACKEND env var."""
    backend_type = os.environ.get("SEARCH_BACKEND", "sqlite").lower()
    if backend_type == "opensearch":
        return OpenSearchBackend()
    return SQLiteBackend()
