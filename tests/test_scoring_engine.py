"""Unit tests for ScoringEngine.score() — no network, no DB."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.scoring.engine import ScoringEngine

# Minimal config that mirrors configs/default.yaml RYG rules.
_CFG = {
    "ryg_rules": {
        "red": {
            "any": [
                {"no_commits_in_days_gte": 7},
                {"ci_latest_conclusion_in": ["failure", "cancelled", "timed_out"]},
            ]
        },
        "yellow": {
            "any": [
                {"no_commits_in_days_gte": 2},
                {"missing_required_files_any": True},
            ]
        },
    },
    "churn_risk_rules": [],
}


def _make_signals(
    days_since_commit: int | None,
    ci_conclusion: str = "success",
    ci_status: str = "success",
    required_files_missing: list[str] | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    last_commit_at = (now - timedelta(days=days_since_commit)) if days_since_commit is not None else None
    return {
        "repo": {"url": "https://github.com/org/repo", "owner": "org", "name": "repo"},
        "captured_at": now,
        "run_id": "test-run-001",
        "last_commit_at": last_commit_at,
        "default_branch": "main",
        "commits_7d": 5 if (days_since_commit is not None and days_since_commit <= 7) else 0,
        "ci_status": ci_status,
        "ci_conclusion": ci_conclusion,
        "required_files_missing": required_files_missing or [],
    }


def _engine() -> ScoringEngine:
    return ScoringEngine(cfg=_CFG)


class TestScoringEngineGreen:
    def test_recent_commit_gives_green(self):
        signals = _make_signals(days_since_commit=1)
        snap = _engine().score(signals)
        assert snap.status_ryg == "green"

    def test_green_explanation_contains_criteria(self):
        signals = _make_signals(days_since_commit=0)
        snap = _engine().score(signals)
        assert snap.status_ryg == "green"
        assert snap.status_explanation  # non-empty


class TestScoringEngineRed:
    def test_stale_repo_is_red(self):
        signals = _make_signals(days_since_commit=30)
        snap = _engine().score(signals)
        assert snap.status_ryg == "red"

    def test_stale_explanation_mentions_days(self):
        signals = _make_signals(days_since_commit=30)
        snap = _engine().score(signals)
        assert "30" in snap.status_explanation or "days" in snap.status_explanation.lower()

    def test_ci_failure_is_red(self):
        signals = _make_signals(days_since_commit=1, ci_conclusion="failure", ci_status="failure")
        snap = _engine().score(signals)
        assert snap.status_ryg == "red"

    def test_no_commit_timestamp_is_red(self):
        # None last_commit_at → engine treats as "no timestamp available" → red
        signals = _make_signals(days_since_commit=None)
        snap = _engine().score(signals)
        assert snap.status_ryg == "red"


class TestScoringEngineYellow:
    def test_slightly_stale_is_yellow(self):
        # 4 days: >= 2 (yellow threshold) but < 7 (red threshold)
        signals = _make_signals(days_since_commit=4)
        snap = _engine().score(signals)
        assert snap.status_ryg == "yellow"

    def test_missing_required_files_is_yellow(self):
        signals = _make_signals(days_since_commit=1, required_files_missing=["docs/architecture.md"])
        snap = _engine().score(signals)
        assert snap.status_ryg == "yellow"


class TestScoringEngineSnapshot:
    def test_snapshot_carries_repo_ref(self):
        signals = _make_signals(days_since_commit=1)
        snap = _engine().score(signals)
        assert snap.repo.owner == "org"
        assert snap.repo.name == "repo"

    def test_snapshot_has_run_id(self):
        signals = _make_signals(days_since_commit=1)
        snap = _engine().score(signals)
        assert snap.run_id == "test-run-001"
