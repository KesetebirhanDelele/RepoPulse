"""Unit tests for ReleasesCollector — no network, no DB."""

from __future__ import annotations

from app.collector.releases import ReleasesCollector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(enabled: bool) -> dict:
    return {"collection": {"releases": {"enabled": enabled}}}


class _Exc(Exception):
    """Fake HTTP exception with a .response.status_code attribute."""
    def __init__(self, status_code: int) -> None:
        self.response = type("R", (), {"status_code": status_code})()


class FakeGitHubClient:
    """Minimal stand-in for GitHubClient.  Behaviour keyed on URL path."""

    def __init__(self, tags_result, releases_result) -> None:
        # tags_result: list to return, or an Exception subclass to raise
        # releases_result: dict to return, or an Exception subclass to raise
        self._tags = tags_result
        self._releases = releases_result

    def get_json(self, path: str, params=None):
        if "/tags" in path:
            if isinstance(self._tags, BaseException):
                raise self._tags
            return self._tags
        if "/releases/latest" in path:
            if isinstance(self._releases, BaseException):
                raise self._releases
            return self._releases
        raise ValueError(f"Unexpected path: {path}")


def _signals() -> dict:
    return {"repo": {"owner": "org", "name": "repo"}}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestReleasesCollector:

    def test_disabled_returns_signals_unchanged(self):
        gh = FakeGitHubClient(tags_result=[{"name": "v1.0"}], releases_result={"tag_name": "v1.0"})
        collector = ReleasesCollector(gh)
        sig = _signals()
        result = collector.enrich(sig)
        assert "latest_tag" not in result
        assert "latest_release" not in result

    def test_disabled_config(self):
        gh = FakeGitHubClient(tags_result=[{"name": "v1.0"}], releases_result={"tag_name": "v1.0"})
        collector = ReleasesCollector(gh)
        sig = _signals()
        result = collector.enrich(sig, cfg=_cfg(False))
        assert "latest_tag" not in result
        assert "latest_release" not in result

    def test_tag_and_release_returned(self):
        gh = FakeGitHubClient(
            tags_result=[{"name": "v0.3.0"}],
            releases_result={"tag_name": "v0.3.0"},
        )
        collector = ReleasesCollector(gh)
        sig = _signals()
        result = collector.enrich(sig, cfg=_cfg(True))
        assert result["latest_tag"] == "v0.3.0"
        assert result["latest_release"] == "v0.3.0"

    def test_empty_tags_and_404_release(self):
        gh = FakeGitHubClient(
            tags_result=[],
            releases_result=_Exc(404),
        )
        collector = ReleasesCollector(gh)
        sig = _signals()
        result = collector.enrich(sig, cfg=_cfg(True))
        assert result["latest_tag"] is None
        assert result["latest_release"] is None

    def test_tags_exception_still_tries_release(self):
        gh = FakeGitHubClient(
            tags_result=_Exc(500),
            releases_result={"tag_name": "v2.1.0"},
        )
        collector = ReleasesCollector(gh)
        sig = _signals()
        result = collector.enrich(sig, cfg=_cfg(True))
        assert result["latest_tag"] is None
        assert result["latest_release"] == "v2.1.0"

    def test_release_uses_name_when_tag_name_absent(self):
        gh = FakeGitHubClient(
            tags_result=[],
            releases_result={"name": "Release 1.0"},
        )
        collector = ReleasesCollector(gh)
        sig = _signals()
        result = collector.enrich(sig, cfg=_cfg(True))
        assert result["latest_release"] == "Release 1.0"
