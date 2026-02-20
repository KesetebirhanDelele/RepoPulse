"""Database initialisation: create tables if they don't exist."""

import sqlite3
from pathlib import Path


def init_db(db_path: Path) -> None:
    """Ensure the parent directory exists and create all required tables."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS repos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                url             TEXT,
                owner           TEXT,
                name            TEXT,
                dev_owner_name  TEXT,
                team            TEXT
            );

            CREATE TABLE IF NOT EXISTS runs (
                run_id              TEXT PRIMARY KEY,
                started_at          TEXT,
                finished_at         TEXT,
                failures_json       TEXT,
                outputs_json        TEXT,
                api_mode            TEXT,
                config_used_path    TEXT,
                config_hash         TEXT,
                signals_used_path   TEXT,
                signals_hash        TEXT,
                repos_used_path     TEXT,
                repos_hash          TEXT,
                scoring_version     TEXT,
                db_path             TEXT
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                run_id          TEXT,
                captured_at     TEXT,
                owner           TEXT,
                name            TEXT,
                snapshot_json   TEXT,
                PRIMARY KEY (run_id, owner, name)
            );
            """
        )
        con.commit()
    finally:
        con.close()
