from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
import yaml

from app.github.github_client import GitHubClient

class CommitsCollector:
    def __init__(self, gh: GitHubClient):
        self.gh = gh

    def enrich(self, signals: dict[str, Any], signals_path) -> dict[str, Any]:
        cfg = yaml.safe_load(open(signals_path, "r", encoding="utf-8"))
        if not cfg["collection"]["commits"]["enabled"]:
            return signals

        repo = signals["repo"]
        owner, name = repo["owner"], repo["name"]

        repo_meta = self.gh.get_json(f"/repos/{owner}/{name}")
        default_branch = repo_meta.get("default_branch")

        now = datetime.now(timezone.utc)
        since_24h = (now - timedelta(hours=24)).isoformat()
        since_7d = (now - timedelta(days=7)).isoformat()

        commits_24h = self.gh.get_json(
            f"/repos/{owner}/{name}/commits",
            params={"sha": default_branch, "since": since_24h, "per_page": 100},
        )
        commits_7d = self.gh.get_json(
            f"/repos/{owner}/{name}/commits",
            params={"sha": default_branch, "since": since_7d, "per_page": 100},
        )

        last_commit_at = None
        if commits_7d:
            # GitHub returns newest-first
            dt = commits_7d[0]["commit"]["committer"]["date"]
            last_commit_at = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        else:
            # No commits in the last 7 days — fetch the single most recent commit
            # so scoring can compute how stale the repo actually is.
            recent = self.gh.get_json(
                f"/repos/{owner}/{name}/commits",
                params={"sha": default_branch, "per_page": 1},
            )
            if recent:
                dt = recent[0]["commit"]["committer"]["date"]
                last_commit_at = datetime.fromisoformat(dt.replace("Z", "+00:00"))

        # Top files changed: fetch commit detail for top N recent in 24h window
        max_details = int(cfg["collection"]["commits"]["max_commit_details"])
        file_counts: dict[str, int] = {}
        for c in commits_24h[:max_details]:
            sha = c["sha"]
            detail = self.gh.get_json(f"/repos/{owner}/{name}/commits/{sha}")
            for f in detail.get("files", []) or []:
                fn = f.get("filename")
                if fn:
                    file_counts[fn] = file_counts.get(fn, 0) + 1

        top_files_24h = [k for k, _ in sorted(file_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]]

        # Minimal evidence bundle (collector-level)
        signals.update({
            "default_branch": default_branch,
            "last_commit_at": last_commit_at,
            "commits_24h": len(commits_24h),
            "commits_7d": len(commits_7d),
            "top_files_24h": top_files_24h,
        })
        return signals