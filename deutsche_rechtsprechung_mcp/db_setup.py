"""
Automatic database setup.

On first run, downloads the pre-built SQLite database from a GitHub Release
so that end users don't need to run the data preprocessing pipeline.

If the database already exists, this is a no-op.
"""

import os
import sys
import sqlite3
import urllib.request
import zipfile
import tempfile

from deutsche_rechtsprechung_mcp.paths import get_data_dir, get_db_path

# URL of the pre-built database (ZIP-compressed).
# This should point to a GitHub Release asset.
# Set RECHTSPRECHUNG_DB_URL to override.
DEFAULT_DB_URL = os.environ.get(
    "RECHTSPRECHUNG_DB_URL",
    "https://github.com/MansKos/deutsche-rechtsprechung-mcp/releases/download/v0.1.0/decisions.db.zip",
)


def _download_db(url: str, dest_path: str) -> None:
    """Download and extract the database ZIP to dest_path."""
    data_dir = os.path.dirname(dest_path)
    os.makedirs(data_dir, exist_ok=True)

    print(
        f"Datenbank wird heruntergeladen...\n"
        f"  Quelle: {url}\n"
        f"  Ziel:   {dest_path}\n"
        f"  (Dies geschieht nur beim ersten Start und kann einige Minuten dauern.)",
        file=sys.stderr,
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = os.path.join(tmp_dir, "db.zip")

        # Download with progress
        def _reporthook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded * 100 // total_size)
                mb = downloaded / (1024 * 1024)
                total_mb = total_size / (1024 * 1024)
                print(
                    f"\r  Fortschritt: {mb:.0f}/{total_mb:.0f} MB ({pct}%)",
                    end="",
                    file=sys.stderr,
                )
            else:
                mb = downloaded / (1024 * 1024)
                print(f"\r  Heruntergeladen: {mb:.0f} MB", end="", file=sys.stderr)

        try:
            urllib.request.urlretrieve(url, zip_path, reporthook=_reporthook)
            print("", file=sys.stderr)  # newline after progress
        except Exception as e:
            print(f"\n  Fehler beim Download: {e}", file=sys.stderr)
            print(
                "  Die Datenbank konnte nicht heruntergeladen werden.\n"
                "  Bitte laden Sie sie manuell herunter und legen Sie sie ab unter:\n"
                f"    {dest_path}\n"
                "  Oder setzen Sie RECHTSPRECHUNG_DB_URL auf eine gültige URL.",
                file=sys.stderr,
            )
            raise

        # Extract
        print("  Entpacke Datenbank...", file=sys.stderr)
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Find the .db file in the archive
            db_files = [n for n in zf.namelist() if n.endswith(".db")]
            if not db_files:
                raise RuntimeError("ZIP-Archiv enthält keine .db-Datei")
            zf.extract(db_files[0], tmp_dir)
            extracted = os.path.join(tmp_dir, db_files[0])
            # Move to final location
            os.replace(extracted, dest_path)

    print(f"  Datenbank bereit: {dest_path}", file=sys.stderr)


def _verify_db(db_path: str) -> bool:
    """Quick check that the database is valid and has data."""
    try:
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def ensure_database() -> str:
    """
    Ensure the SQLite database exists and is valid.

    Returns the path to the database.
    """
    db_path = get_db_path()

    if os.path.exists(db_path) and _verify_db(db_path):
        return db_path

    # Remove corrupt/empty database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    _download_db(DEFAULT_DB_URL, db_path)

    if not _verify_db(db_path):
        raise RuntimeError(
            f"Datenbank unter {db_path} ist leer oder beschädigt. "
            "Bitte löschen und erneut herunterladen."
        )

    return db_path
