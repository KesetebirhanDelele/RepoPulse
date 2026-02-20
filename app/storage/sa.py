"""SQLAlchemy engine setup and DDL initialisation for RepoPulse."""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_engine(db_url: str) -> Engine:
    """Return a SQLAlchemy 2.0 engine for the given URL."""
    return create_engine(db_url, future=True)


def init_db(engine: Engine) -> None:
    """Create all required tables if they do not already exist."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS repos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                url             TEXT,
                owner           TEXT,
                name            TEXT,
                dev_owner_name  TEXT,
                team            TEXT
            )
        """))
        conn.execute(text("""
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
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS snapshots (
                run_id          TEXT,
                captured_at     TEXT,
                owner           TEXT,
                name            TEXT,
                snapshot_json   TEXT,
                PRIMARY KEY (run_id, owner, name)
            )
        """))
