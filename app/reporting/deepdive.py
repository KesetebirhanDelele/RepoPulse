"""Deep-dive queue CSV export.

Queries the latest snapshot per repo from the DB, filters to repos that need
attention (red/yellow status or active risk flags), and writes a prioritised
CSV for the engineering review queue.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.settings import Settings
from app.storage.sa import get_engine

_FIELDS = ["owner", "name", "team", "dev_owner_name", "status_ryg", "reason", "captured_at"]

_RYG_ORDER = {"red": 0, "yellow": 1, "green": 2}

# SQL: one row per (owner, name) at its latest captured_at
_LATEST_SNAPSHOTS_SQL = text("""
    SELECT s.owner, s.name, s.captured_at, s.snapshot_json
    FROM snapshots s
    INNER JOIN (
        SELECT owner, name, MAX(captured_at) AS max_cap
        FROM snapshots
        GROUP BY owner, name
    ) latest
        ON  s.owner      = latest.owner
        AND s.name       = latest.name
        AND s.captured_at = latest.max_cap
""")


def _build_reason(snap: dict[str, Any]) -> str:
    parts: list[str] = []

    explanation = (snap.get("status_explanation") or "").strip()
    if explanation:
        parts.append(explanation)

    ci_status = snap.get("ci_status") or ""
    if ci_status and ci_status != "none":
        parts.append(f"CI: {ci_status}")

    missing = snap.get("required_files_missing") or []
    if missing:
        parts.append(f"Missing docs: {len(missing)}")

    risk_flags = snap.get("risk_flags") or []
    if risk_flags:
        ids = ", ".join(
            rf.get("id") or rf.get("label") or "?"
            for rf in risk_flags
            if isinstance(rf, dict)
        )
        if ids:
            parts.append(f"Risks: {ids}")

    return " | ".join(parts)


def _needs_deepdive(snap: dict[str, Any]) -> bool:
    return snap.get("status_ryg") in ("yellow", "red") or bool(
        snap.get("risk_flags")
    )


def export_deepdive_queue_csv(db_path: Path, out_path: Path) -> None:
    """Write the deep-dive queue CSV for repos needing attention.

    Args:
        db_path: Ignored — connection uses Settings().db_url.  Kept for
                 backward-compatible call signature.
        out_path: Destination CSV file.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    engine = get_engine(Settings().db_url)
    rows: list[dict[str, Any]] = []

    with engine.connect() as conn:
        result = conn.execute(_LATEST_SNAPSHOTS_SQL)
        for db_row in result:
            try:
                snap: dict[str, Any] = json.loads(db_row.snapshot_json)
            except Exception:
                continue  # skip malformed rows

            if not _needs_deepdive(snap):
                continue

            repo = snap.get("repo") or {}
            rows.append(
                {
                    "owner": db_row.owner,
                    "name": db_row.name,
                    "team": repo.get("team") or "",
                    "dev_owner_name": repo.get("dev_owner_name") or "",
                    "status_ryg": snap.get("status_ryg", ""),
                    "reason": _build_reason(snap),
                    "captured_at": db_row.captured_at,
                }
            )

    rows.sort(key=lambda r: (_RYG_ORDER.get(r["status_ryg"], 9), r["owner"], r["name"]))

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
