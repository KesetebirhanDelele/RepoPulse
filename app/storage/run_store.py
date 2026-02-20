"""Persistence for pipeline runs."""

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _file_hash(path: Path) -> str:
    """Return hex sha256 of a file's bytes, or '' if the file doesn't exist."""
    p = Path(path)
    if not p.exists():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


class RunStore:
    """Read/write pipeline run rows."""

    def __init__(self, db_path: Path) -> None:
        self._db = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db)

    def start_run(
        self,
        repos_path: Path,
        config_path: Path,
        signals_path: Path,
        db_path: Path,
        api_mode: str = "token",
        scoring_version: str = "1.0",
    ) -> str:
        """Insert a new run row and return its run_id (UUID4 string)."""
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()

        con = self._connect()
        try:
            con.execute(
                """
                INSERT INTO runs (
                    run_id, started_at, api_mode,
                    config_used_path, config_hash,
                    signals_used_path, signals_hash,
                    repos_used_path, repos_hash,
                    scoring_version, db_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    started_at,
                    api_mode,
                    str(config_path),
                    _file_hash(config_path),
                    str(signals_path),
                    _file_hash(signals_path),
                    str(repos_path),
                    _file_hash(repos_path),
                    scoring_version,
                    str(db_path),
                ),
            )
            con.commit()
        finally:
            con.close()

        return run_id

    def finish_run(
        self,
        run_id: str,
        failures: list[dict],
        outputs: dict,
    ) -> None:
        """Set finished_at and persist failures/outputs for an existing run."""
        finished_at = datetime.now(timezone.utc).isoformat()
        con = self._connect()
        try:
            con.execute(
                """
                UPDATE runs
                SET finished_at   = ?,
                    failures_json = ?,
                    outputs_json  = ?
                WHERE run_id = ?
                """,
                (
                    finished_at,
                    json.dumps(failures),
                    json.dumps(outputs),
                    run_id,
                ),
            )
            con.commit()
        finally:
            con.close()
