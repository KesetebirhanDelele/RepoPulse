"""Persistence for repo snapshots."""

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.settings import Settings
from app.storage.sa import get_engine


class SnapshotStore:
    """Read/write snapshot rows."""

    def __init__(self, db_path_or_url: "str | Path") -> None:
        if isinstance(db_path_or_url, Path):
            db_url = Settings().db_url
        elif "://" in db_path_or_url:
            db_url = db_path_or_url
        else:
            db_url = "sqlite:///" + Path(db_path_or_url).resolve().as_posix()
        self._engine = get_engine(db_url)

    def upsert_snapshot(self, snapshot) -> None:
        """Insert or replace a snapshot row.

        Accepts a Pydantic model (uses .model_dump()) or a plain dict.
        Expects the snapshot to contain ``run_id``, ``owner``, and ``name``
        at the top level (or nested under ``repo``).
        """
        if hasattr(snapshot, "model_dump"):
            data: dict = snapshot.model_dump()
        else:
            data = dict(snapshot)

        repo = data.get("repo", {})
        run_id: str = str(data.get("run_id", ""))
        owner: str = data.get("owner") or repo.get("owner", "")
        name: str = data.get("name") or repo.get("name", "")
        captured_at_raw = data.get("captured_at")
        if isinstance(captured_at_raw, datetime):
            captured_at = captured_at_raw.isoformat()
        elif captured_at_raw is None:
            captured_at = datetime.now(timezone.utc).isoformat()
        else:
            captured_at = str(captured_at_raw)

        with self._engine.begin() as conn:
            conn.execute(
                text("""
                    DELETE FROM snapshots
                    WHERE run_id = :run_id AND owner = :owner AND name = :name
                """),
                {"run_id": run_id, "owner": owner, "name": name},
            )
            conn.execute(
                text("""
                    INSERT INTO snapshots (run_id, captured_at, owner, name, snapshot_json)
                    VALUES (:run_id, :captured_at, :owner, :name, :snapshot_json)
                """),
                {
                    "run_id": run_id,
                    "captured_at": captured_at,
                    "owner": owner,
                    "name": name,
                    "snapshot_json": json.dumps(data, default=str),
                },
            )
