"""Persistence for pipeline runs."""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.settings import Settings
from app.storage.sa import get_engine


def _file_hash(path: Path) -> str:
    """Return hex sha256 of a file's bytes, or '' if the file doesn't exist."""
    p = Path(path)
    if not p.exists():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


class RunStore:
    """Read/write pipeline run rows."""

    def __init__(self, db_path_or_url: "str | Path") -> None:
        if isinstance(db_path_or_url, Path):
            db_url = Settings().db_url
        elif "://" in db_path_or_url:
            db_url = db_path_or_url
        else:
            db_url = "sqlite:///" + Path(db_path_or_url).resolve().as_posix()
        self._engine = get_engine(db_url)

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

        with self._engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO runs (
                        run_id, started_at, api_mode,
                        config_used_path, config_hash,
                        signals_used_path, signals_hash,
                        repos_used_path, repos_hash,
                        scoring_version, db_path
                    ) VALUES (
                        :run_id, :started_at, :api_mode,
                        :config_used_path, :config_hash,
                        :signals_used_path, :signals_hash,
                        :repos_used_path, :repos_hash,
                        :scoring_version, :db_path
                    )
                """),
                {
                    "run_id": run_id,
                    "started_at": started_at,
                    "api_mode": api_mode,
                    "config_used_path": str(config_path),
                    "config_hash": _file_hash(config_path),
                    "signals_used_path": str(signals_path),
                    "signals_hash": _file_hash(signals_path),
                    "repos_used_path": str(repos_path),
                    "repos_hash": _file_hash(repos_path),
                    "scoring_version": scoring_version,
                    "db_path": str(db_path),
                },
            )

        return run_id

    def finish_run(
        self,
        run_id: str,
        failures: list[dict],
        outputs: dict,
    ) -> None:
        """Set finished_at and persist failures/outputs for an existing run."""
        finished_at = datetime.now(timezone.utc).isoformat()

        with self._engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE runs
                    SET finished_at   = :finished_at,
                        failures_json = :failures_json,
                        outputs_json  = :outputs_json
                    WHERE run_id = :run_id
                """),
                {
                    "finished_at": finished_at,
                    "failures_json": json.dumps(failures),
                    "outputs_json": json.dumps(outputs),
                    "run_id": run_id,
                },
            )
