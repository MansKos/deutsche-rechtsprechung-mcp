"""
Data directory and database path resolution.

Uses platform-appropriate data directories:
- Linux:   ~/.local/share/deutsche-rechtsprechung/
- macOS:   ~/Library/Application Support/deutsche-rechtsprechung/
- Windows: %LOCALAPPDATA%/deutsche-rechtsprechung/

Override with SQLITE_DB_PATH env var.
"""

import os
import sys


def get_data_dir() -> str:
    """Return the platform-appropriate data directory."""
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


def get_db_path() -> str:
    """Return the path to the SQLite database."""
    env_path = os.environ.get("SQLITE_DB_PATH")
    if env_path:
        return env_path
    return os.path.join(get_data_dir(), "decisions.db")
