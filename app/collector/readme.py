"""Stub collector for README health signals."""

from __future__ import annotations

from typing import Any
import yaml


class ReadmeCollector:
    """Enriches signals with README presence and freshness indicators."""

    def __init__(self, gh) -> None:
        self.gh = gh

    def enrich(self, signals: dict[str, Any], signals_path) -> dict[str, Any]:
        """Add README fields to signals if collection.readme.enabled is true."""
        cfg = yaml.safe_load(open(signals_path, "r", encoding="utf-8"))
        if not cfg.get("collection", {}).get("readme", {}).get("enabled", False):
            return signals

        signals.update(
            {
                "readme_sha": None,
                "readme_updated_within_7d": None,
                "readme_status_block_present": None,
                "readme_status_block_updated_within_7d": None,
            }
        )
        return signals
