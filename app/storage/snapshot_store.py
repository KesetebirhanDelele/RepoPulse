"""Persistence for repo snapshots."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SnapshotStore:
    """Read/write snapshot rows."""

    def __init__(self, db_path: Path) -> None:
        self._db = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db)

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

        con = self._connect()
        try:
            con.execute(
                """
                INSERT INTO snapshots (run_id, captured_at, owner, name, snapshot_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id, owner, name) DO UPDATE SET
                    captured_at   = excluded.captured_at,
                    snapshot_json = excluded.snapshot_json
                """,
                (run_id, captured_at, owner, name, json.dumps(data, default=str)),
            )
            con.commit()
        finally:
            con.close()
