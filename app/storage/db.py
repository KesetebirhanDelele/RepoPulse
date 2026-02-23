"""Database initialisation: create tables if they don't exist."""

from pathlib import Path

from app.settings import Settings
from app.storage import sa


def init_db(db_path: Path) -> None:
    """Initialise the database using SQLAlchemy.

    db_path is accepted for API compatibility but the engine URL is sourced
    from Settings (env var DB_URL or the default sqlite URL). Settings also
    ensures the data/ directory exists for the default sqlite case.
    """
    engine = sa.get_engine(Settings().db_url)
    sa.init_db(engine)
    sa.migrate_db(engine)
