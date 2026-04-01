"""Docker entry point for SQLite ingestion."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from deutsche_rechtsprechung_mcp.ingest_sqlite import main

if __name__ == "__main__":
    main()
