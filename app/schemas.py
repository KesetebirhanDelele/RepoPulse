# app/schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

RYG = Literal["green", "yellow", "red"]
CIStatus = Literal["success", "failure", "none", "unknown"]
IssueCount = int | Literal["n/a"]

class RepoRef(BaseModel):
    url: str
    owner: str
    name: str
    dev_owner_name: Optional[str] = None
    team: Optional[str] = None
    project_name: Optional[str] = None
    target_milestone: Optional[str] = None
    due_date: Optional[str] = None  # keep as string for MVP (ISO date)

class SignalEvidence(BaseModel):
    key: str
    value: Any
    source: Optional[str] = None     # e.g., endpoint name
    collected_at: datetime

class RiskFlag(BaseModel):
    id: str
    label: str
    severity: RYG
    message: str
    evidence: list[SignalEvidence] = Field(default_factory=list)

class RepoSnapshot(BaseModel):
    run_id: str
    captured_at: datetime
    repo: RepoRef

    default_branch: Optional[str] = None
    last_commit_at: Optional[datetime] = None
    commits_24h: Optional[int] = None
    commits_7d: Optional[int] = None

    top_files_24h: list[str] = Field(default_factory=list)
    top_files_7d: list[str] = Field(default_factory=list)

    ci_status: CIStatus = "unknown"
    ci_conclusion: Optional[str] = None
    ci_updated_at: Optional[datetime] = None

    open_issues: IssueCount = "n/a"
    blocked_issues: IssueCount = "n/a"

    latest_tag: Optional[str] = None
    latest_release: Optional[str] = None

    readme_sha: Optional[str] = None
    readme_updated_within_7d: Optional[bool] = None
    readme_status_block_present: Optional[bool] = None
    readme_status_block_updated_within_7d: Optional[bool] = None

    required_files_missing: list[str] = Field(default_factory=list)
    required_globs_missing: list[str] = Field(default_factory=list)

    # Derived
    status_ryg: RYG
    status_explanation: str
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    evidence: list[SignalEvidence] = Field(default_factory=list)

class WeeklyReportRow(BaseModel):
    week_start: str
    week_end: str
    repo: RepoRef

    commits_since_since_date: int
    commits_7d: int
    last_commit_at: Optional[datetime] = None
    ci_status: CIStatus = "unknown"
    latest_tag_or_release: Optional[str] = None

    readme_updated_week: Optional[bool] = None
    top_files_changed_week: list[str] = Field(default_factory=list)

    status_ryg: RYG
    status_explanation: str
    risk_flags: list[str] = Field(default_factory=list)  # flattened for CSV

class RunMetadata(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None

    repos_processed: int
    failures: list[dict[str, str]] = Field(default_factory=list)  # {repo, error}

    config_used_path: str
    config_hash: str
    signals_used_path: str
    signals_hash: str
    repos_used_path: str
    repos_hash: str

    api_mode: Literal["token", "no-token"]
    scoring_version: str

    db_path: str
    outputs: dict[str, str] = Field(default_factory=dict)  # {latest_csv, weekly_csv, deepdive_csv}