"""Weekly rollup CSV export (MVP stub)."""

import csv
from pathlib import Path

_FIELDS = ["week_start", "week_end", "owner", "name", "status_ryg"]


def export_weekly_csv(db_path: Path, since_date: str, out_path: Path) -> None:
    """Write an empty weekly CSV with headers.

    Real DB aggregation will be implemented in a later iteration.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
