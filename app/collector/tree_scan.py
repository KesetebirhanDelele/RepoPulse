"""Collector for repo file-tree compliance signals."""

from __future__ import annotations

from typing import Any
import yaml


class TreeScanCollector:
    """Enriches signals with required-file and required-glob presence checks."""

    def __init__(self, gh) -> None:
        self.gh = gh

    def _exists(self, owner: str, name: str, path: str) -> bool:
        """Return True if the given path exists at the repo root via Contents API."""
        try:
            self.gh.get_json(f"/repos/{owner}/{name}/contents/{path}")
            return True
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code == 404:
                return False
            # Unexpected error — treat as absent
            return False

    def enrich(self, signals: dict[str, Any], signals_path) -> dict[str, Any]:
        """Add tree-scan fields to signals if collection.tree_scan.enabled is true."""
        cfg = yaml.safe_load(open(signals_path, "r", encoding="utf-8"))
        if not cfg.get("collection", {}).get("tree_scan", {}).get("enabled", False):
            return signals

        repo = signals["repo"]
        owner, name = repo["owner"], repo["name"]

        gitignore_present = self._exists(owner, name, ".gitignore")
        env_example_present = (
            self._exists(owner, name, ".env.example")
            or self._exists(owner, name, "env.example")
        )

        signals.update(
            {
                "required_files_missing": [],
                "required_globs_missing": [],
                "gitignore_present": gitignore_present,
                "env_example_present": env_example_present,
            }
        )
        return signals
