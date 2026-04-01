"""
Ingest Markdown + JSON files into a SQLite FTS5 database.

Usage:
    python src/ingest_sqlite.py

Environment variables:
    MARKDOWN_DIR  – directory containing the markdown files (default: ../markdown)
    SQLITE_DB_PATH – path to the SQLite database file (default: data/decisions.db)
"""

import os
import glob
import json
import sqlite3
import sys

MARKDOWN_DIR = os.environ.get("MARKDOWN_DIR", os.path.join(os.path.dirname(__file__), "..", "markdown"))
DB_PATH = os.environ.get(
    "SQLITE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "decisions.db"),
)


def create_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS decisions (
            doknr       TEXT PRIMARY KEY,
            title       TEXT,
            ecli        TEXT,
            az          TEXT,
            datum       TEXT,
            gericht     TEXT,
            spruchkoerper TEXT,
            normen      TEXT,
            leitsatz    TEXT,
            sonstosatz  TEXT,
            tenor       TEXT,
            tatbestand  TEXT,
            entscheidungsgruende TEXT,
            gruende     TEXT,
            abwmeinung  TEXT,
            sonstlt     TEXT,
            full_text   TEXT
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
            title,
            az,
            full_text,
            normen,
            leitsatz,
            content='decisions',
            content_rowid='rowid',
            tokenize='unicode61'
        );

        -- Triggers to keep FTS in sync with the main table
        CREATE TRIGGER IF NOT EXISTS decisions_ai AFTER INSERT ON decisions BEGIN
            INSERT INTO decisions_fts(rowid, title, az, full_text, normen, leitsatz)
            VALUES (new.rowid, new.title, new.az, new.full_text, new.normen, new.leitsatz);
        END;

        CREATE TRIGGER IF NOT EXISTS decisions_ad AFTER DELETE ON decisions BEGIN
            INSERT INTO decisions_fts(decisions_fts, rowid, title, az, full_text, normen, leitsatz)
            VALUES ('delete', old.rowid, old.title, old.az, old.full_text, old.normen, old.leitsatz);
        END;

        CREATE TRIGGER IF NOT EXISTS decisions_au AFTER UPDATE ON decisions BEGIN
            INSERT INTO decisions_fts(decisions_fts, rowid, title, az, full_text, normen, leitsatz)
            VALUES ('delete', old.rowid, old.title, old.az, old.full_text, old.normen, old.leitsatz);
            INSERT INTO decisions_fts(rowid, title, az, full_text, normen, leitsatz)
            VALUES (new.rowid, new.title, new.az, new.full_text, new.normen, new.leitsatz);
        END;
    """)


def ingest(conn: sqlite3.Connection):
    files = glob.iglob(os.path.join(MARKDOWN_DIR, "**", "*.md"), recursive=True)
    count = 0
    skipped = 0

    for md_path in files:
        json_path = os.path.splitext(md_path)[0] + ".json"
        if not os.path.exists(json_path):
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            with open(md_path, "r", encoding="utf-8") as f:
                full_text = f.read()

            doknr = metadata.get("doknr")
            if not doknr:
                skipped += 1
                continue

            gericht = f"{metadata.get('gertyp', '')} {metadata.get('gerort', '')}".strip()

            conn.execute(
                """
                INSERT OR REPLACE INTO decisions
                    (doknr, title, ecli, az, datum, gericht, spruchkoerper, normen,
                     leitsatz, sonstosatz, tenor, tatbestand, entscheidungsgruende,
                     gruende, abwmeinung, sonstlt, full_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doknr,
                    metadata.get("title"),
                    metadata.get("ecli"),
                    metadata.get("aktenzeichen"),
                    metadata.get("datum"),
                    gericht,
                    metadata.get("spruchkoerper"),
                    metadata.get("norm"),
                    metadata.get("leitsatz"),
                    metadata.get("sonstosatz"),
                    metadata.get("tenor"),
                    metadata.get("tatbestand"),
                    metadata.get("entscheidungsgruende"),
                    metadata.get("gruende"),
                    metadata.get("abwmeinung"),
                    metadata.get("sonstlt"),
                    full_text,
                ),
            )

            count += 1
            if count % 500 == 0:
                conn.commit()
                print(f"  {count} Entscheidungen importiert...")

        except Exception as e:
            print(f"Fehler bei {md_path}: {e}", file=sys.stderr)
            skipped += 1

    conn.commit()
    print(f"Import abgeschlossen: {count} importiert, {skipped} übersprungen.")


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if os.path.exists(DB_PATH):
        print(f"Datenbank {DB_PATH} existiert bereits. Überspringe Import.")
        print("Löschen Sie die Datei, um einen Neuimport zu starten.")
        return

    print(f"Erstelle SQLite-Datenbank: {DB_PATH}")
    print(f"Markdown-Verzeichnis: {MARKDOWN_DIR}")

    conn = sqlite3.connect(DB_PATH)
    try:
        # Enable WAL mode for better concurrent read performance
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        create_tables(conn)
        ingest(conn)

        # Optimize FTS index after bulk insert
        print("Optimiere FTS-Index...")
        conn.execute("INSERT INTO decisions_fts(decisions_fts) VALUES('optimize')")
        conn.commit()
        print("Fertig.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
