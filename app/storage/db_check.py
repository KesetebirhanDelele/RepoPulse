"""Health-check helper: connect to the configured DB and report table counts."""

import re
from sqlalchemy import text

from app.storage.sa import get_engine


def _redact_url(url: str) -> str:
    """Replace password in a DB URL with *** so it is safe to print."""
    return re.sub(r"(://[^:]+:)[^@]+(@)", r"\1***\2", url)


def run_db_check(db_url: str) -> None:
    engine = get_engine(db_url)
    print(f"db_url:     {_redact_url(db_url)}")
    with engine.connect() as conn:
        for table in ("repos", "runs", "snapshots"):
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"{table + ':':12} {count}")
