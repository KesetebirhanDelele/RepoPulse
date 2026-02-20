"""SQLAlchemy engine setup and DDL initialisation for RepoPulse."""

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine
from sqlalchemy.engine import Engine

metadata = MetaData()

Table(
    "repos",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("url", Text),
    Column("owner", String),
    Column("name", String),
    Column("dev_owner_name", String),
    Column("team", String),
)

Table(
    "runs",
    metadata,
    Column("run_id", String, primary_key=True),
    Column("started_at", String),
    Column("finished_at", String),
    Column("failures_json", Text),
    Column("outputs_json", Text),
    Column("api_mode", String),
    Column("config_used_path", String),
    Column("config_hash", String),
    Column("signals_used_path", String),
    Column("signals_hash", String),
    Column("repos_used_path", String),
    Column("repos_hash", String),
    Column("scoring_version", String),
    Column("db_path", String),
)

Table(
    "snapshots",
    metadata,
    Column("run_id", String, primary_key=True),
    Column("captured_at", String),
    Column("owner", String, primary_key=True),
    Column("name", String, primary_key=True),
    Column("snapshot_json", Text),
)


def get_engine(db_url: str) -> Engine:
    """Return a SQLAlchemy 2.0 engine for the given URL."""
    return create_engine(db_url, future=True)


def init_db(engine: Engine) -> None:
    """Create all required tables if they do not already exist."""
    metadata.create_all(engine)
