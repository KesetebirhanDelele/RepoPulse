# app/storage/repo_store.py
"""Persistence for tracked repositories."""

from pathlib import Path

import yaml
from sqlalchemy import text

from app.settings import Settings
from app.storage.sa import get_engine

from app.settings import Settings
from pathlib import Path

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
    """Read/write repo rows via SQLAlchemy."""

    def __init__(self, db_path_or_url: "str | Path") -> None:
        if isinstance(db_path_or_url, Path):
            db_url = Settings().db_url
        elif "://" in db_path_or_url:
            db_url = db_path_or_url
        else:
            db_url = "sqlite:///" + Path(db_path_or_url).resolve().as_posix()
        self._engine = get_engine(db_url)

    def add_repo(
        self,
        url: str,
        owner: str,
        name: str = "",
        dev_owner_name: str | None = None,
        team: str | None = None,
    ) -> None:
        """Insert a repo by (owner, name); silently skips on conflict."""
        with self._engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO repos (url, owner, name, dev_owner_name, team)
                    VALUES (:url, :owner, :name, :dev_owner_name, :team)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "url": url,
                    "owner": owner,
                    "name": name,
                    "dev_owner_name": dev_owner_name,
                    "team": team,
                },
            )

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

        count = 0
        with self._engine.begin() as conn:
            for r in repos:
                conn.execute(
                    text("""
                        INSERT INTO repos (url, owner, name, dev_owner_name, team)
                        VALUES (:url, :owner, :name, :dev_owner_name, :team)
                        ON CONFLICT(id) DO UPDATE SET
                            url            = excluded.url,
                            dev_owner_name = excluded.dev_owner_name,
                            team           = excluded.team
                    """),
                    {
                        "url": r.get("url", ""),
                        "owner": r.get("owner", ""),
                        "name": r.get("name", ""),
                        "dev_owner_name": r.get("dev_owner_name"),
                        "team": r.get("team"),
                    },
                )
                count += 1
        return count

    def list_repos(self) -> list[dict]:
        """Return all repos as a list of dicts with keys owner, name, url, dev_owner_name, team."""
        with self._engine.begin() as conn:
            rows = conn.execute(
                text("SELECT owner, name, url, dev_owner_name, team FROM repos")
            ).mappings().all()
        return [dict(r) for r in rows]
