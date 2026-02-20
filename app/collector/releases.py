"""Stub collector for GitHub Releases signals."""

from __future__ import annotations

from typing import Any
import yaml


class ReleasesCollector:
    """Enriches signals with latest release/tag information."""

    def __init__(self, gh) -> None:
        self.gh = gh

    def enrich(self, signals: dict[str, Any], signals_path) -> dict[str, Any]:
        """Add release fields to signals if collection.releases.enabled is true."""
        cfg = yaml.safe_load(open(signals_path, "r", encoding="utf-8"))
        if not cfg.get("collection", {}).get("releases", {}).get("enabled", False):
            return signals

        signals.update(
            {
                "latest_tag": None,
                "latest_release": None,
            }
        )
        return signals
