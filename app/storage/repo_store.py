"""Persistence for tracked repositories."""

import sqlite3
from pathlib import Path

import yaml


def _project_root() -> Path:
    """Walk upward from this file's directory to find the directory containing pyproject.toml."""
    current = Path(__file__).resolve().parent
    while True:
        if (current / "pyproject.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            return Path.cwd()
        current = parent


class RepoStore:
    """Read/write repo rows."""

    def __init__(self, db_path: Path) -> None:
        self._db = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self._db)
        con.row_factory = sqlite3.Row
        return con

    def add_repo(
        self,
        url: str,
        owner: str,
        name: str = "",
        dev_owner_name: str | None = None,
        team: str | None = None,
    ) -> None:
        """Insert or replace a repo by (owner, name)."""
        con = self._connect()
        try:
            con.execute(
                """
                INSERT INTO repos (url, owner, name, dev_owner_name, team)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """,
                (url, owner, name, dev_owner_name, team),
            )
            con.commit()
        finally:
            con.close()

    def import_from_yaml(self, path: Path) -> int:
        """Parse a YAML list of repos and upsert each into the repos table.

        Each entry must have at least ``url``, ``owner``, and ``name``.
        Returns the number of rows inserted/updated.
        """
        path = Path(path)
        if not path.is_absolute():
            path = _project_root() / path
        if not path.exists():
            raise FileNotFoundError(
                f"Repos YAML not found: {path.as_posix()!r} "
                f"(cwd={Path.cwd().as_posix()!r}). "
                "Check that the file exists in the configs directory."
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        repos: list[dict] = data if isinstance(data, list) else data.get("repos", [])

        con = self._connect()
        count = 0
        try:
            for r in repos:
                con.execute(
                    """
                    INSERT INTO repos (url, owner, name, dev_owner_name, team)
                    VALUES (:url, :owner, :name, :dev_owner_name, :team)
                    ON CONFLICT(id) DO UPDATE SET
                        url           = excluded.url,
                        dev_owner_name= excluded.dev_owner_name,
                        team          = excluded.team
                    """,
                    {
                        "url": r.get("url", ""),
                        "owner": r.get("owner", ""),
                        "name": r.get("name", ""),
                        "dev_owner_name": r.get("dev_owner_name"),
                        "team": r.get("team"),
                    },
                )
                count += 1
            con.commit()
        finally:
            con.close()

        return count

    def list_repos(self) -> list[dict]:
        """Return all repos as a list of dicts with keys owner, name, url, dev_owner_name, team."""
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT owner, name, url, dev_owner_name, team FROM repos"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            con.close()
