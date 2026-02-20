from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import yaml

from app.schemas import RepoSnapshot

def _file_hash(p: Path) -> str:
    b = p.read_bytes()
    return hashlib.sha256(b).hexdigest()

@dataclass
class ScoringEngine:
    cfg: dict[str, Any]

    @classmethod
    def from_paths(cls, config_path: Path) -> "ScoringEngine":
        cfg = yaml.safe_load(open(config_path, "r", encoding="utf-8"))
        return cls(cfg=cfg)

    def score(self, signals: dict[str, Any]) -> RepoSnapshot:
        repo = signals["repo"]
        captured_at = signals["captured_at"]
        run_id = signals["run_id"]

        last_commit_at = signals.get("last_commit_at")
        now = datetime.now(timezone.utc)

        # Compute "no_commits_in_days" from signals (no hardcoded thresholds)
        no_commits_days = None
        if last_commit_at:
            no_commits_days = (now - last_commit_at).days

        missing_required = signals.get("required_files_missing", [])
        ci_status = signals.get("ci_status", "unknown")
        ci_conclusion = signals.get("ci_conclusion")

        # Evaluate R/Y/G from config rules (generic)
        status, explanation = self._evaluate_ryg(signals, no_commits_days)

        risk_flags = self._evaluate_churn(signals)

        snap = RepoSnapshot(
            run_id=run_id,
            captured_at=captured_at,
            repo=repo,
            default_branch=signals.get("default_branch"),
            last_commit_at=last_commit_at,
            commits_24h=signals.get("commits_24h"),
            commits_7d=signals.get("commits_7d"),
            top_files_24h=signals.get("top_files_24h", []),
            top_files_7d=signals.get("top_files_7d", []),
            ci_status=ci_status,
            ci_conclusion=ci_conclusion,
            ci_updated_at=signals.get("ci_updated_at"),
            open_issues=signals.get("open_issues", "n/a"),
            blocked_issues=signals.get("blocked_issues", "n/a"),
            latest_tag=signals.get("latest_tag"),
            latest_release=signals.get("latest_release"),
            readme_sha=signals.get("readme_sha"),
            readme_updated_within_7d=signals.get("readme_updated_within_7d"),
            readme_status_block_present=signals.get("readme_status_block_present"),
            readme_status_block_updated_within_7d=signals.get("readme_status_block_updated_within_7d"),
            required_files_missing=missing_required,
            required_globs_missing=signals.get("required_globs_missing", []),
            status_ryg=status,
            status_explanation=explanation,
            risk_flags=risk_flags,
            evidence=signals.get("evidence", []),
        )
        return snap

    def _evaluate_ryg(self, signals: dict[str, Any], no_commits_days: int | None) -> tuple[str, str]:
        rules = self.cfg.get("ryg_rules", {})

        # Minimal generic interpreter for MVP: check "red" then "yellow" else green
        # (Still config-driven; no fixed thresholds embedded here.)
        def match_any(block: list[dict[str, Any]]) -> tuple[bool, str]:
            for cond in block:
                ok, msg = self._match_condition(cond, signals, no_commits_days)
                if ok:
                    return True, msg
            return False, ""

        red = rules.get("red", {}).get("any", [])
        yellow = rules.get("yellow", {}).get("any", [])

        ok, msg = match_any(red)
        if ok:
            return "red", msg

        ok, msg = match_any(yellow)
        if ok:
            return "yellow", msg

        return "green", "Meets configured freshness/CI/docs criteria."

    def _match_condition(self, cond: dict[str, Any], signals: dict[str, Any], no_commits_days: int | None) -> tuple[bool, str]:
        if "no_commits_in_days_gte" in cond:
            v = cond["no_commits_in_days_gte"]
            if no_commits_days is None:
                return True, "No commit timestamp available."
            return (no_commits_days >= v), f"No commits in {no_commits_days} days (>= {v})."

        if "ci_latest_conclusion_in" in cond:
            concl = (signals.get("ci_conclusion") or "").lower()
            vals = [x.lower() for x in cond["ci_latest_conclusion_in"]]
            return (concl in vals), f"CI conclusion is {concl}."

        if "missing_required_files_any" in cond:
            missing = signals.get("required_files_missing", [])
            return (len(missing) > 0), f"Missing required docs: {', '.join(missing)}"

        if "ci_missing" in cond:
            return (signals.get("ci_status") == "none"), "CI workflow missing."

        if "ci_ok_or_missing_allowed" in cond:
            # For MVP, treat success/none as ok; real policy can be config-expanded later
            return (signals.get("ci_status") in ["success", "none"]), "CI ok or not present."

        return False, "No matching condition."

    def _evaluate_churn(self, signals: dict[str, Any]) -> list:
        # Keep MVP simple: create RiskFlag objects only when rule matches.
        # Full rule engine can be expanded incrementally.
        from app.schemas import RiskFlag, SignalEvidence
        out = []
        rules = self.cfg.get("churn_risk_rules", [])
        now = datetime.now(timezone.utc)

        commits_7d = int(signals.get("commits_7d") or 0)
        has_tag_or_release = bool(signals.get("latest_tag") or signals.get("latest_release"))

        for r in rules:
            rid = r.get("id", "rule")
            when = r.get("when", {})
            # Example: commits_7d_gte + negate on has_release_or_tag_within_days -> MVP approximates to boolean
            if "commits_7d_gte" in when and commits_7d < int(when["commits_7d_gte"]):
                continue
            if "has_release_or_tag_within_days" in when:
                negate = bool(when.get("negate"))
                if negate and has_tag_or_release:
                    continue
                if (not negate) and (not has_tag_or_release):
                    continue

            out.append(
                RiskFlag(
                    id=rid,
                    label=r.get("label", "risk"),
                    severity=r.get("severity", "yellow"),
                    message=r.get("message", "Rule triggered."),
                    evidence=[
                        SignalEvidence(key="commits_7d", value=commits_7d, source="collector/commits", collected_at=now),
                        SignalEvidence(key="has_tag_or_release", value=has_tag_or_release, source="collector/releases", collected_at=now),
                    ],
                )
            )
        return out