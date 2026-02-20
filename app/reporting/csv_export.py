"""Export the latest snapshot results to CSV."""

import csv
from pathlib import Path

_FIELDS = ["owner", "name", "captured_at", "status_ryg", "status_explanation",
           "commits_24h", "commits_7d", "ci_status"]


def export_latest_snapshot_csv(snapshots, out_path: Path) -> None:
    """Write one CSV row per snapshot.

    Accepts a list of Pydantic models (uses .model_dump()) or plain dicts.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for snap in snapshots:
            row = snap.model_dump() if hasattr(snap, "model_dump") else dict(snap)
            # Flatten nested repo fields if present
            repo = row.get("repo", {})
            if isinstance(repo, dict):
                row.setdefault("owner", repo.get("owner", ""))
                row.setdefault("name", repo.get("name", ""))
            writer.writerow({k: row.get(k, "") for k in _FIELDS})
