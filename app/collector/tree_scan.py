"""Collector for repo file-tree compliance signals."""

from __future__ import annotations

from typing import Any
import yaml

_REQUIRED_DOCS = [
    "docs/architecture.md",
    "docs/data-model.md",
    "docs/operations.md",
]

_README_PATTERNS = ["README.md", "README.rst", "README.txt", "README"]

_TEST_INDICATORS = [
    "tests",
    "test",
    "__tests__",
    "pytest.ini",
    "package.json",
    "pyproject.toml",
]


class TreeScanCollector:
    """Enriches signals with required-file and required-glob presence checks."""

    def __init__(self, gh) -> None:
        self.gh = gh

    def _exists(self, owner: str, name: str, path: str) -> bool:
        """Return True if path exists at the repo root via Contents API."""
        try:
            self.gh.get_json(f"/repos/{owner}/{name}/contents/{path}")
            return True
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code == 404:
                return False
            return False  # unexpected error — treat as absent

    def _env_not_tracked(self, owner: str, name: str) -> bool:
        """Return True (safe) when .env is absent; False when it is present in the repo."""
        try:
            self.gh.get_json(f"/repos/{owner}/{name}/contents/.env")
            return False  # .env found — it IS tracked (bad)
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code == 404:
                return True  # .env absent — not tracked (good)
            return True  # unexpected error — fail-open

    def enrich(self, signals: dict[str, Any], signals_path) -> dict[str, Any]:
        """Add tree-scan fields to signals if collection.tree_scan.enabled is true."""
        cfg = yaml.safe_load(open(signals_path, "r", encoding="utf-8"))
        if not cfg.get("collection", {}).get("tree_scan", {}).get("enabled", False):
            return signals

        repo = signals["repo"]
        owner, name = repo["owner"], repo["name"]

        try:
            readme_present = any(
                self._exists(owner, name, p) for p in _README_PATTERNS
            )
            tests_present = any(
                self._exists(owner, name, p) for p in _TEST_INDICATORS
            )
            docs_missing = [
                doc for doc in _REQUIRED_DOCS
                if not self._exists(owner, name, doc)
            ]
            gitignore_present = self._exists(owner, name, ".gitignore")
            env_not_tracked = self._env_not_tracked(owner, name)
        except Exception:
            readme_present = False
            tests_present = False
            docs_missing = list(_REQUIRED_DOCS)
            gitignore_present = False
            env_not_tracked = True

        signals.update(
            {
                "required_files_missing": [],
                "required_globs_missing": [],
                "readme_present": readme_present,
                "tests_present": tests_present,
                "docs_missing": docs_missing,
                "gitignore_present": gitignore_present,
                "env_not_tracked": env_not_tracked,
            }
        )
        return signals
