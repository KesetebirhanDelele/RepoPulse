"""Weekly rollup CSV export.

Queries all snapshots captured on or after since_date, selects the latest per
repo, and writes a prioritised CSV sorted by status then owner/name.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.settings import Settings
from app.storage.sa import get_engine

_FIELDS = [
    "week_start",
    "owner",
    "name",
    "team",
    "dev_owner_name",
    "captured_at",
    "commits_7d",
    "last_commit_at",
    "ci_status",
    "latest_tag",
    "latest_release",
    "top_files_7d",
    "status_ryg",
    "status_explanation",
    "risk_flags",
    "readme_present",
    "tests_present",
    "docs_missing",
    "gitignore_present",
    "env_not_tracked",
]

_RYG_ORDER = {"red": 0, "yellow": 1, "green": 2}

_SINCE_SQL = text("""
    SELECT s.owner, s.name, s.captured_at, s.snapshot_json
    FROM snapshots s
    INNER JOIN (
        SELECT owner, name, MAX(captured_at) AS max_cap
        FROM snapshots
        WHERE captured_at >= :since
        GROUP BY owner, name
    ) latest
        ON  s.owner       = latest.owner
        AND s.name        = latest.name
        AND s.captured_at = latest.max_cap
    WHERE s.captured_at >= :since
""")


_DOCS_DEFAULT = "docs/architecture.md;docs/data-model.md;docs/operations.md"


def _risk_ids(risk_flags: list[Any]) -> str:
    parts: list[str] = []
    for rf in risk_flags:
        if isinstance(rf, dict):
            parts.append(rf.get("id") or rf.get("label") or "?")
    return ";".join(parts)


def _format_hygiene(snap: dict[str, Any]) -> dict[str, str]:
    """Return CSV-formatted hygiene fields extracted from a snapshot dict."""
    docs = snap.get("docs_missing")
    return {
        "readme_present": "true" if snap.get("readme_present") is True else "false",
        "tests_present": "true" if snap.get("tests_present") is True else "false",
        "docs_missing": ";".join(docs) if isinstance(docs, list) else _DOCS_DEFAULT,
        "gitignore_present": "true" if snap.get("gitignore_present") is True else "false",
        "env_not_tracked": "true" if snap.get("env_not_tracked", True) is not False else "false",
    }


def export_weekly_csv(db_path: Path, since_date: str, out_path: Path) -> None:
    """Write a weekly rollup CSV for all repos with snapshots since since_date.

    Args:
        db_path: Ignored — connection uses Settings().db_url.  Kept for
                 backward-compatible call signature.
        since_date: ISO date string (YYYY-MM-DD) used as the window start.
        out_path: Destination CSV file.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    engine = get_engine(Settings().db_url)
    rows: list[dict[str, Any]] = []

    with engine.connect() as conn:
        result = conn.execute(_SINCE_SQL, {"since": since_date})
        for db_row in result:
            try:
                snap: dict[str, Any] = json.loads(db_row.snapshot_json)
            except Exception:
                continue  # skip malformed rows

            repo = snap.get("repo") or {}
            top_files = snap.get("top_files_7d") or []
            risk_flags = snap.get("risk_flags") or []

            latest_tag = snap.get("latest_tag") or ""
            latest_release = snap.get("latest_release") or ""

            rows.append(
                {
                    "week_start": since_date,
                    "owner": db_row.owner,
                    "name": db_row.name,
                    "team": repo.get("team") or "",
                    "dev_owner_name": repo.get("dev_owner_name") or "",
                    "captured_at": db_row.captured_at,
                    "commits_7d": snap.get("commits_7d") if snap.get("commits_7d") is not None else "",
                    "last_commit_at": snap.get("last_commit_at") or "",
                    "ci_status": snap.get("ci_status") or "",
                    "latest_tag": latest_tag,
                    "latest_release": latest_release,
                    "top_files_7d": ";".join(top_files) if isinstance(top_files, list) else str(top_files),
                    "status_ryg": snap.get("status_ryg") or "",
                    "status_explanation": snap.get("status_explanation") or "",
                    "risk_flags": _risk_ids(risk_flags),
                    **_format_hygiene(snap),
                }
            )

    rows.sort(
        key=lambda r: (_RYG_ORDER.get(r["status_ryg"], 9), r["owner"], r["name"])
    )

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
