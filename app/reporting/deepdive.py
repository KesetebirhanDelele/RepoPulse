"""Deep-dive queue CSV export (MVP stub)."""

import csv
from pathlib import Path

_FIELDS = ["owner", "name", "status_ryg", "reason"]


def export_deepdive_queue_csv(db_path: Path, out_path: Path) -> None:
    """Write an empty deep-dive queue CSV with headers.

    Real DB query will be implemented in a later iteration.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
