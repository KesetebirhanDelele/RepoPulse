"""Collector for GitHub Actions CI signals.

Fetches the latest workflow run for a repo and maps it to a normalised
ci_status / ci_conclusion / ci_updated_at triple.  The collector is
optional: if collection.actions.enabled is false in signals.yaml the
signals dict is returned unchanged.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import yaml

_FAILURE_CONCLUSIONS = {
    "failure", "cancelled", "timed_out", "action_required",
    "stale", "skipped", "neutral",
}
_IN_FLIGHT_STATUSES = {"queued", "in_progress"}


def _map_ci_status(conclusion: str | None, status: str | None) -> str:
    if conclusion == "success":
        return "success"
    if conclusion in _FAILURE_CONCLUSIONS:
        return "failure"
    if status in _IN_FLIGHT_STATUSES:
        return "unknown"
    return "unknown"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # GitHub uses "Z" suffix; replace for broad Python compat (<3.11)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ActionsCollector:
    """Enriches signals with CI/CD status from GitHub Actions."""

    def __init__(self, gh) -> None:
        self.gh = gh

    def enrich(self, signals: dict[str, Any], signals_path) -> dict[str, Any]:
        """Add CI fields to signals if collection.actions.enabled is true."""
        cfg = yaml.safe_load(open(signals_path, "r", encoding="utf-8"))
        if not cfg.get("collection", {}).get("actions", {}).get("enabled", False):
            return signals

        repo = signals["repo"]
        owner, name = repo["owner"], repo["name"]

        try:
            data = self.gh.get_json(
                f"/repos/{owner}/{name}/actions/runs",
                params={"per_page": 1},
            )
            runs = data.get("workflow_runs", [])
        except Exception as exc:
            # 404 = Actions not enabled for this repo; surface as "none"
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code == 404:
                signals.update({"ci_status": "none", "ci_conclusion": None, "ci_updated_at": None})
            else:
                signals.update({"ci_status": "unknown", "ci_conclusion": None, "ci_updated_at": None})
            return signals

        if not runs:
            signals.update({"ci_status": "none", "ci_conclusion": None, "ci_updated_at": None})
            return signals

        run = runs[0]
        conclusion = run.get("conclusion")
        status = run.get("status")
        signals.update(
            {
                "ci_status": _map_ci_status(conclusion, status),
                "ci_conclusion": conclusion or status,
                "ci_updated_at": _parse_dt(run.get("updated_at")),
            }
        )
        return signals
