"""Stub collector for GitHub Actions CI signals."""

from __future__ import annotations

from typing import Any
import yaml


class ActionsCollector:
    """Enriches signals with CI/CD status from GitHub Actions."""

    def __init__(self, gh) -> None:
        self.gh = gh

    def enrich(self, signals: dict[str, Any], signals_path) -> dict[str, Any]:
        """Add CI fields to signals if collection.actions.enabled is true."""
        cfg = yaml.safe_load(open(signals_path, "r", encoding="utf-8"))
        if not cfg.get("collection", {}).get("actions", {}).get("enabled", False):
            return signals

        signals.update(
            {
                "ci_status": "none",
                "ci_conclusion": None,
                "ci_updated_at": None,
            }
        )
        return signals
