"""Validation logic for RepoPulse config files.

Returns a list of Result objects; callers decide how to render and exit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_KNOWN_COLLECTOR_KEYS = ["commits", "actions", "releases", "readme", "tree_scan"]


@dataclass
class Result:
    level: str   # "OK" | "WARN" | "ERROR"
    path: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level:<5}] {self.path}: {self.message}"


def _load_yaml(path: Path) -> tuple[Any, str | None]:
    """Return (parsed, error_message). error_message is None on success."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh), None
    except yaml.YAMLError as exc:
        return None, f"YAML parse error: {exc}"
    except OSError as exc:
        return None, f"Cannot read file: {exc}"


def _check_repos(path: Path) -> list[Result]:
    results: list[Result] = []
    label = str(path)

    if not path.exists():
        results.append(Result("ERROR", label, "File not found"))
        return results

    data, err = _load_yaml(path)
    if err:
        results.append(Result("ERROR", label, err))
        return results

    if not isinstance(data, list):
        results.append(Result("ERROR", label, f"Expected a list of repos, got {type(data).__name__}"))
        return results

    if len(data) == 0:
        results.append(Result("WARN", label, "Repo list is empty"))
        return results

    bad: list[str] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            bad.append(f"item[{i}] is not a dict")
            continue
        for required_field in ("url", "owner", "name"):
            if not item.get(required_field):
                bad.append(f"item[{i}] missing '{required_field}'")

    if bad:
        results.append(Result("ERROR", label, "; ".join(bad)))
    else:
        results.append(Result("OK", label, f"{len(data)} repo(s) — all required fields present"))

    return results


def _check_signals(path: Path) -> list[Result]:
    results: list[Result] = []
    label = str(path)

    if not path.exists():
        results.append(Result("ERROR", label, "File not found"))
        return results

    data, err = _load_yaml(path)
    if err:
        results.append(Result("ERROR", label, err))
        return results

    if not isinstance(data, dict) or "collection" not in data:
        results.append(Result("ERROR", label, "Missing top-level 'collection' key"))
        return results

    collection = data["collection"]
    if not isinstance(collection, dict):
        results.append(Result("ERROR", label, "'collection' must be a mapping"))
        return results

    warnings: list[str] = []
    for key in _KNOWN_COLLECTOR_KEYS:
        entry = collection.get(key)
        if entry is None:
            warnings.append(f"'{key}' not present (defaults to disabled)")
        elif not isinstance(entry, dict):
            warnings.append(f"'{key}' should be a mapping")
        elif "enabled" not in entry:
            warnings.append(f"'{key}.enabled' not set (defaults to false)")
        elif not isinstance(entry["enabled"], bool):
            warnings.append(f"'{key}.enabled' should be a boolean")

    if warnings:
        results.append(Result("WARN", label, "; ".join(warnings)))
    else:
        results.append(Result("OK", label, "collection keys present with boolean 'enabled' flags"))

    return results


def _check_default(path: Path) -> list[Result]:
    results: list[Result] = []
    label = str(path)

    if not path.exists():
        results.append(Result("ERROR", label, "File not found"))
        return results

    data, err = _load_yaml(path)
    if err:
        results.append(Result("ERROR", label, err))
        return results

    if not isinstance(data, dict):
        results.append(Result("ERROR", label, f"Expected a mapping, got {type(data).__name__}"))
        return results

    warnings: list[str] = []
    if "thresholds" not in data:
        warnings.append("'thresholds' key missing")
    if "ryg_rules" not in data:
        warnings.append("'ryg_rules' key missing")

    if warnings:
        results.append(Result("WARN", label, "; ".join(warnings)))
    else:
        results.append(Result("OK", label, "'thresholds' and 'ryg_rules' present"))

    return results


def validate_all(
    repos_path: Path = Path("configs/repos.yaml"),
    signals_path: Path = Path("configs/signals.yaml"),
    default_path: Path = Path("configs/default.yaml"),
) -> list[Result]:
    """Run all checks and return results."""
    results: list[Result] = []
    results.extend(_check_repos(repos_path))
    results.extend(_check_signals(signals_path))
    results.extend(_check_default(default_path))
    return results
