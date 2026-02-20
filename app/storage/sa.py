"""SQLAlchemy engine setup and DDL initialisation for RepoPulse."""

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine
from sqlalchemy.engine import Engine

metadata = MetaData()

Table(
    "repos",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("url", Text),
    Column("owner", String(255)),
    Column("name", String(255)),
    Column("dev_owner_name", String(255)),
    Column("team", String(255)),
)

Table(
    "runs",
    metadata,
    Column("run_id", String(36), primary_key=True),
    Column("started_at", String(64)),
    Column("finished_at", String(64)),
    Column("failures_json", Text),
    Column("outputs_json", Text),
    Column("api_mode", String(20)),
    Column("config_used_path", String(512)),
    Column("config_hash", String(64)),
    Column("signals_used_path", String(512)),
    Column("signals_hash", String(64)),
    Column("repos_used_path", String(512)),
    Column("repos_hash", String(64)),
    Column("scoring_version", String(50)),
    Column("db_path", String(512)),
)

Table(
    "snapshots",
    metadata,
    Column("run_id", String(36), primary_key=True),
    Column("captured_at", String(64)),
    Column("owner", String(255), primary_key=True),
    Column("name", String(255), primary_key=True),
    Column("snapshot_json", Text),
)


def get_engine(db_url: str) -> Engine:
    """Return a SQLAlchemy 2.0 engine for the given URL."""
    return create_engine(db_url, future=True)


def init_db(engine: Engine) -> None:
    """Create all required tables if they do not already exist."""
    metadata.create_all(engine)
