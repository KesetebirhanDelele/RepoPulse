"""Stub collector for GitHub Releases signals."""

from __future__ import annotations

from typing import Any
import yaml


class ReleasesCollector:
    """Enriches signals with latest release/tag information."""

    def __init__(self, gh) -> None:
        self.gh = gh

    def enrich(
        self,
        signals: dict[str, Any],
        signals_path: str | None = None,
        cfg: dict | None = None,
    ) -> dict[str, Any]:
        """Add release fields to signals if collection.releases.enabled is true."""
        if cfg is not None:
            pass  # use cfg as-is
        elif signals_path is not None:
            cfg = yaml.safe_load(open(signals_path, "r", encoding="utf-8"))
        else:
            cfg = {}
        if not cfg.get("collection", {}).get("releases", {}).get("enabled", False):
            return signals

        repo = signals["repo"]
        owner, name = repo["owner"], repo["name"]

        # Fetch latest tag
        latest_tag = None
        try:
            tags = self.gh.get_json(
                f"/repos/{owner}/{name}/tags",
                params={"per_page": 1},
            )
            if tags:
                latest_tag = tags[0]["name"]
        except Exception:
            latest_tag = None

        # Fetch latest GitHub release
        latest_release = None
        try:
            release = self.gh.get_json(f"/repos/{owner}/{name}/releases/latest")
            latest_release = release.get("tag_name") or release.get("name") or None
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            latest_release = None  # 404 (no releases) or any other error

        signals.update({"latest_tag": latest_tag, "latest_release": latest_release})
        return signals
