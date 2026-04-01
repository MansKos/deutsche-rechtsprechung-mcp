#!/bin/bash
# Start script that selects the right ingestion based on the search backend.

SEARCH_BACKEND="${SEARCH_BACKEND:-sqlite}"

if [ "$SEARCH_BACKEND" = "opensearch" ]; then
    echo "Backend: OpenSearch"
    echo "Running OpenSearch Ingestion..."
    python src/ingest.py
else
    echo "Backend: SQLite"
    echo "Running SQLite Ingestion..."
    python src/ingest_sqlite.py
fi

echo "Starting MCP Server..."
python src/server.py
