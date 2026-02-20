"""Stub collector for repo file-tree compliance signals."""

from __future__ import annotations

from typing import Any
import yaml


class TreeScanCollector:
    """Enriches signals with required-file and required-glob presence checks."""

    def __init__(self, gh) -> None:
        self.gh = gh

    def enrich(self, signals: dict[str, Any], signals_path) -> dict[str, Any]:
        """Add tree-scan fields to signals if collection.tree_scan.enabled is true."""
        cfg = yaml.safe_load(open(signals_path, "r", encoding="utf-8"))
        if not cfg.get("collection", {}).get("tree_scan", {}).get("enabled", False):
            return signals

        signals.update(
            {
                "required_files_missing": [],
                "required_globs_missing": [],
            }
        )
        return signals
