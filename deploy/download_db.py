"""Download the pre-built SQLite database if it doesn't exist."""

import os
import sys
import sqlite3
import urllib.request
import zipfile
import tempfile

DATA_DIR = os.environ.get("RECHTSPRECHUNG_DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "decisions.db")
DB_URL = os.environ.get(
    "RECHTSPRECHUNG_DB_URL",
    "https://github.com/MansKos/deutsche-rechtsprechung-mcp/releases/download/v0.1.0/decisions.db.zip",
)


def db_is_valid():
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def download():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Downloading database from {DB_URL}...")

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "db.zip")

        def progress(block, block_size, total):
            if total > 0:
                pct = min(100, block * block_size * 100 // total)
                print(f"\r  {pct}%", end="", flush=True)

        urllib.request.urlretrieve(DB_URL, zip_path, reporthook=progress)
        print()

        with zipfile.ZipFile(zip_path, "r") as zf:
            db_files = [n for n in zf.namelist() if n.endswith(".db")]
            if not db_files:
                print("ERROR: ZIP contains no .db file", file=sys.stderr)
                sys.exit(1)
            zf.extract(db_files[0], tmp)
            os.replace(os.path.join(tmp, db_files[0]), DB_PATH)

    print(f"Database ready: {DB_PATH}")


if __name__ == "__main__":
    if db_is_valid():
        print(f"Database already exists: {DB_PATH}")
    else:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        download()
