"""
Ingest Markdown + JSON files into a SQLite FTS5 database.

Usage:
    deutsche-rechtsprechung-ingest

Environment variables:
    MARKDOWN_DIR       – directory containing the markdown files
    SQLITE_DB_PATH     – path to the SQLite database file
"""

import os
import glob
import json
import sqlite3
import sys

from deutsche_rechtsprechung_mcp.paths import get_db_path


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


def ingest(conn: sqlite3.Connection, markdown_dir: str):
    files = glob.iglob(os.path.join(markdown_dir, "**", "*.md"), recursive=True)
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
    markdown_dir = os.environ.get("MARKDOWN_DIR")
    if not markdown_dir:
        print(
            "Bitte setzen Sie MARKDOWN_DIR auf das Verzeichnis mit den Markdown-Dateien.\n"
            "Beispiel: MARKDOWN_DIR=./mcp/markdown deutsche-rechtsprechung-ingest",
            file=sys.stderr,
        )
        sys.exit(1)

    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    if os.path.exists(db_path):
        print(f"Datenbank {db_path} existiert bereits. Überspringe Import.")
        print("Löschen Sie die Datei, um einen Neuimport zu starten.")
        return

    print(f"Erstelle SQLite-Datenbank: {db_path}")
    print(f"Markdown-Verzeichnis: {markdown_dir}")

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        create_tables(conn)
        ingest(conn, markdown_dir)
        print("Optimiere FTS-Index...")
        conn.execute("INSERT INTO decisions_fts(decisions_fts) VALUES('optimize')")
        conn.commit()
        print("Fertig.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
