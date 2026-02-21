"""Collector for repo file-tree compliance signals."""

from __future__ import annotations

import re
from typing import Any
import yaml

_REQUIRED_DOCS = [
    "docs/architecture.md",
    "docs/data-model.md",
    "docs/operations.md",
]

_README_PATTERNS = ["README.md", "README.rst", "README.txt", "README"]

# Directories whose mere presence indicates tests exist (checked via Contents API).
_TEST_DIR_NAMES = ["tests", "test", "__tests__"]

# File-pattern regexes applied against every blob path in the git tree.
_TEST_FILE_REGEXES = [
    re.compile(r"(^|/)test_[^/]+\.py$"),       # Python: test_*.py
    re.compile(r"(^|/)[^/]+_test\.py$"),        # Python: *_test.py
    re.compile(r"(^|/)[^/]+\.spec\.(js|jsx|ts|tsx)$"),   # JS/TS spec
    re.compile(r"(^|/)[^/]+\.test\.(js|jsx|ts|tsx)$"),   # JS/TS test
    re.compile(r"(^|/)[^/]+_test\.go$"),        # Go
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

    def _get_tree_paths(self, owner: str, name: str, default_branch: str) -> list[str] | None:
        """Fetch the full recursive git tree; return list of blob paths or None on failure."""
        try:
            data = self.gh.get_json(
                f"/repos/{owner}/{name}/git/trees/{default_branch}",
                params={"recursive": "1"},
            )
            # Truncated trees are unreliable for absence checks — treat as failure.
            if data.get("truncated"):
                return None
            return [entry["path"] for entry in data.get("tree", []) if entry.get("type") == "blob"]
        except Exception:
            return None

    def _tests_present_from_tree(self, paths: list[str]) -> bool:
        """Return True if any path matches a known test-file pattern."""
        for path in paths:
            for pattern in _TEST_FILE_REGEXES:
                if pattern.search(path):
                    return True
        return False

    def _tests_present_dirs_only(self, owner: str, name: str) -> bool:
        """Fallback: check whether any test directory exists via Contents API."""
        return any(self._exists(owner, name, d) for d in _TEST_DIR_NAMES)

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

            # Determine tests_present using git tree (accurate) with directory fallback.
            default_branch = signals.get("default_branch") or "main"
            tree_paths = self._get_tree_paths(owner, name, default_branch)
            if tree_paths is not None:
                tests_present = (
                    self._tests_present_from_tree(tree_paths)
                    or any(
                        any(
                            part == d
                            for part in p.split("/")
                        )
                        for p in tree_paths
                        for d in _TEST_DIR_NAMES
                    )
                )
            else:
                tests_present = self._tests_present_dirs_only(owner, name)

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
