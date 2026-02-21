"""Unit tests for pure reporting helpers — no network, no DB."""

from __future__ import annotations

import pytest

from app.reporting.deepdive import _build_reason
from app.reporting.weekly import _DOCS_DEFAULT, _format_hygiene


# ---------------------------------------------------------------------------
# _build_reason (deepdive)
# ---------------------------------------------------------------------------

class TestBuildReason:
    def test_empty_snap_returns_empty_string(self):
        assert _build_reason({}) == ""

    def test_explanation_included(self):
        snap = {"status_explanation": "No commits in 30 days", "ci_status": "none"}
        reason = _build_reason(snap)
        assert "No commits in 30 days" in reason

    def test_ci_status_included_when_not_none(self):
        snap = {"ci_status": "failure"}
        reason = _build_reason(snap)
        assert "CI: failure" in reason

    def test_ci_status_none_excluded(self):
        snap = {"ci_status": "none"}
        reason = _build_reason(snap)
        assert "CI" not in reason

    def test_missing_docs_count_included(self):
        snap = {"required_files_missing": ["docs/architecture.md", "docs/runbook.md"]}
        reason = _build_reason(snap)
        assert "Missing docs: 2" in reason

    def test_risk_flags_ids_included(self):
        snap = {
            "risk_flags": [
                {"id": "high_commits_no_release", "label": "churn_risk"},
                {"id": "refactor_heavy", "label": "churn_risk"},
            ]
        }
        reason = _build_reason(snap)
        assert "high_commits_no_release" in reason
        assert "refactor_heavy" in reason

    def test_all_parts_pipe_separated(self):
        snap = {
            "status_explanation": "Stale",
            "ci_status": "failure",
            "required_files_missing": ["docs/arch.md"],
            "risk_flags": [{"id": "risk_x"}],
        }
        reason = _build_reason(snap)
        parts = reason.split(" | ")
        assert len(parts) == 4

    def test_risk_flag_missing_id_uses_label(self):
        snap = {"risk_flags": [{"label": "churn_risk"}]}
        reason = _build_reason(snap)
        assert "churn_risk" in reason

    def test_non_dict_risk_flags_skipped(self):
        snap = {"risk_flags": ["string_flag", None, {"id": "valid"}]}
        reason = _build_reason(snap)
        assert "valid" in reason


# ---------------------------------------------------------------------------
# _format_hygiene (weekly)
# ---------------------------------------------------------------------------

class TestFormatHygiene:
    def test_all_true_returns_true_strings(self):
        snap = {
            "readme_present": True,
            "tests_present": True,
            "docs_missing": [],
            "gitignore_present": True,
            "env_not_tracked": True,
        }
        result = _format_hygiene(snap)
        assert result["readme_present"] == "true"
        assert result["tests_present"] == "true"
        assert result["gitignore_present"] == "true"
        assert result["env_not_tracked"] == "true"

    def test_false_values_return_false_strings(self):
        snap = {
            "readme_present": False,
            "tests_present": False,
            "docs_missing": [],
            "gitignore_present": False,
            "env_not_tracked": False,
        }
        result = _format_hygiene(snap)
        assert result["readme_present"] == "false"
        assert result["tests_present"] == "false"
        assert result["gitignore_present"] == "false"
        assert result["env_not_tracked"] == "false"

    def test_none_values_return_false(self):
        snap = {}
        result = _format_hygiene(snap)
        assert result["readme_present"] == "false"
        assert result["tests_present"] == "false"
        assert result["gitignore_present"] == "false"

    def test_none_env_not_tracked_returns_false(self):
        # env_not_tracked=None: `is not False` is True → "true"
        snap = {"env_not_tracked": None}
        result = _format_hygiene(snap)
        assert result["env_not_tracked"] == "true"

    def test_docs_missing_list_joined_with_semicolons(self):
        snap = {"docs_missing": ["docs/architecture.md", "docs/data-model.md"]}
        result = _format_hygiene(snap)
        assert result["docs_missing"] == "docs/architecture.md;docs/data-model.md"

    def test_docs_missing_empty_list_returns_empty(self):
        snap = {"docs_missing": []}
        result = _format_hygiene(snap)
        assert result["docs_missing"] == ""

    def test_docs_missing_absent_returns_default(self):
        snap = {}
        result = _format_hygiene(snap)
        assert result["docs_missing"] == _DOCS_DEFAULT

    def test_returned_keys_match_expected_fields(self):
        result = _format_hygiene({})
        assert set(result.keys()) == {
            "readme_present",
            "tests_present",
            "docs_missing",
            "gitignore_present",
            "env_not_tracked",
        }
