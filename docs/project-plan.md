Executive summary (RepoPulse)

RepoPulse is a GitHub-portfolio tracking tool that helps engineering/product leaders spot delivery risk early and focus support where it improves outcomes. It ingests signals from many public repos (activity, CI, releases/tags, and repo hygiene), scores each repo red/yellow/green with human-readable explanations, and stores snapshots in SQL Server for repeatable reporting. It outputs weekly/deepdive CSVs and a lightweight web dashboard for portfolio triage and drilldowns. The plan below organizes work into five milestones with validation gates and milestone demos, with releases/versions aligned to incremental value. Risks are primarily API reliability/rate limits, data consistency across collectors, and adoption (teams keeping metadata up to date).

Timeline at a glance (4 weeks, 1-week sprints)

Scale definition (realistic scale): support 30 repos in one run with stable results and usable dashboard/reporting.

Week 1 — M1 (Plan + requirements) → R1 v0.1.0

Lock scope, config conventions, DB schema, and quality gates

Week 2 — M2 (MVP end-to-end) → R2 v0.2.0

Collect → score → persist → export reports reliably for a small set (3–5 repos)

Week 3 — M3 (Portfolio readiness) → R3 v0.3.0

Run reliably at realistic scale (30 repos), dashboard usable, drilldowns and triage views

Week 4 — M4 (Operational readiness) + start M5 → R4 v0.4.0

Hardening, docs/runbooks, tests/validation command, release discipline; adoption package

Post-week 4 — M5 (Adoption & scale) → R5 v1.0.0

Templates, onboarding workflow, governance signals, and usage guidance for teams

Tickets (copy/pasteable)
1) T1 — Define configs + acceptance criteria

Milestone: M1 | Release: R1 | Version: v0.1.0 | Tags: M1;planning;config;acceptance
Purpose: Establish the rules of the system so outputs are consistent and non-debatable.
Deliverables

Define config files and formats (repos list, signals toggles, thresholds/rules).

Write acceptance criteria for MVP outputs (CSV columns, dashboard views, DB tables).
Tests/Validation

Validate sample configs parse and match schema (manual + config validator command later).

2) T2 — Data model + storage contract

Milestone: M1 | Release: R1 | Version: v0.1.0 | Tags: M1;data-model;db;contract
Purpose: Ensure snapshots are reproducible and reporting doesn’t depend on live API calls.
Deliverables

Tables: repos, runs, snapshots (latest snapshot JSON per repo/run).

Pydantic schema for snapshot JSON (explicit fields; no silent drops).
Tests/Validation

Unit test: “collector signal → snapshot schema retains fields → JSON persists”.

3) T3 — GitHub client reliability baseline

Milestone: M2 | Release: R2 | Version: v0.2.0 | Tags: M2;github;hardening;retries
Purpose: Avoid brittle runs due to transient failures/rate limits.
Deliverables

GitHub client with retry/backoff for 5xx/429 and rate-limit handling.

Clear error messages on terminal failures.
Tests/Validation

Unit tests with mocked http responses for retry conditions (no network).

Manual: run against a few repos, ensure run completes with no flakiness.

4) T4 — Repo ingestion: tracked repos config → DB

Milestone: M2 | Release: R2 | Version: v0.2.0 | Tags: M2;repos;config;db
Purpose: Make tracking configurable and repeatable across teams.
Deliverables

configs/repos.yaml ingestion into repos table.

CLI command(s) to import/list repos.
Tests/Validation

Unit test reading YAML list format and writing expected DB rows (mock DB or temp sqlite).

5) T5 — Commits collector (activity + last commit)

Milestone: M2 | Release: R2 | Version: v0.2.0 | Tags: M2;collector;commits;activity
Purpose: Provide core delivery momentum signals.
Deliverables

commits_24h, commits_7d, last_commit_at

Fallback to fetch most recent commit if commits_7d == 0 so “days stale” is measurable.
Tests/Validation

Unit tests with mocked GitHub responses: active repo, stale repo, missing commits window.

6) T6 — Releases/Tags collector (delivery markers)

Milestone: M2 | Release: R2 | Version: v0.2.0 | Tags: M2;collector;releases;tags
Purpose: Detect shipping checkpoints to distinguish churn vs delivery.
Deliverables

latest_tag, latest_release populated from GitHub APIs

Safe behavior when repos have no tags/releases (None, not failure).
Tests/Validation

Unit tests using a fake client: tag present, release absent, 404 cases, error cases.

7) T7 — Optional CI collector (GitHub Actions)

Milestone: M2 | Release: R2 | Version: v0.2.0 | Tags: M2;collector;ci;optional
Purpose: Surface build health without penalizing repos that don’t use Actions.
Deliverables

ci_status normalized to success/failure/none/unknown from latest workflow run.

Collector toggle via signals config.
Tests/Validation

Unit test mapping logic (status/conclusion → normalized status).

8) T8 — Tree/file audit collector (repo hygiene)

Milestone: M3 | Release: R3 | Version: v0.3.0 | Tags: M3;collector;hygiene;docs;tests
Purpose: Identify support needs (docs/tests/env hygiene) that block delivery and onboarding.
Deliverables

readme_present, tests_present (true only for real tests/dirs/patterns), docs_missing

gitignore_present, env_not_tracked (true when .env is NOT in repo), claude_md_present

Efficient tree scan (low API volume) + safe fallbacks.
Tests/Validation

Unit tests for test-file detection patterns and docs_missing behavior.

9) T9 — Scoring engine: R/Y/G + explanations

Milestone: M2 | Release: R2 | Version: v0.2.0 | Tags: M2;scoring;ryg;rules
Purpose: Convert raw signals into actionable status and reasons.
Deliverables

Config-driven thresholds producing status_ryg and status_explanation

Deterministic outputs for the same snapshot inputs.
Tests/Validation

Unit tests for green/yellow/red scenarios and stable explanations.

10) T10 — Risk flags: portfolio risk taxonomy

Milestone: M3 | Release: R3 | Version: v0.3.0 | Tags: M3;risk;taxonomy;delivery
Purpose: Provide pattern-level risk identification beyond R/Y/G.
Deliverables

Risk flags with evidence: high_commits_no_release, refactor_heavy, contracts_churn(_no_version)

Rule: only emit “*_no_version” when there is no tag/release; otherwise use “contracts_churn”.
Tests/Validation

Unit tests that verify correct flag selection based on latest_tag/latest_release.

11) T11 — Snapshot pipeline + persistence (runs + snapshots)

Milestone: M2 | Release: R2 | Version: v0.2.0 | Tags: M2;pipeline;db;snapshots
Purpose: Make the full run repeatable and auditable.
Deliverables

Run metadata stored in runs, per-repo snapshots stored in snapshots

End-of-run failure summary by category.
Tests/Validation

Manual: run snapshots and confirm DB counts and latest snapshot JSON fields present.

12) T12 — CSV reporting (weekly + deepdive + latest)

Milestone: M3 | Release: R3 | Version: v0.3.0 | Tags: M3;reporting;csv;weekly;deepdive
Purpose: Provide offline decision artifacts for leadership reviews.
Deliverables

Weekly report (one row per repo) from latest snapshots

Deepdive queue prioritized by status/risk, with reasons

Latest snapshot export for quick spreadsheet triage
Tests/Validation

Unit tests for formatting, boolean rendering, docs_missing joining, reason building.

13) T13 — Web dashboard: Portfolio Overview /

Milestone: M3 | Release: R3 | Version: v0.3.0 | Tags: M3;dashboard;portfolio;filters
Purpose: Let leaders answer “where to focus” in seconds.
Deliverables

/ shows one row per repo (latest snapshot), filters (status/team), counters

Columns include project, developer, status, explanation, risk flags, delivery markers (tag/release)
Tests/Validation

Manual: run dashboard locally; verify filtering and correctness vs DB snapshot.

14) T14 — Web dashboard: Audit drilldown /audit

Milestone: M3 | Release: R3 | Version: v0.3.0 | Tags: M3;dashboard;audit;hygiene
Purpose: Provide “what to fix next” per project with ✅/❌.
Deliverables

/audit?owner=...&name=... shows a single-row audit table:
README, Tests, Docs Missing, .gitignore, CLAUDE.md, Env Not Tracked
Tests/Validation

Manual: confirm DB snapshot fields appear and render correctly.

15) T15 — Validate configs command

Milestone: M4 | Release: R4 | Version: v0.4.0 | Tags: M4;ops;validation;config
Purpose: Reduce onboarding friction and misconfig failures.
Deliverables

validate configs command checks existence + structure of core YAML files.
Tests/Validation

Unit test with sample YAML variants; manual run showing OK/WARN/ERROR and exit codes.

16) T16 — Test scaffold + baseline suite (pytest)

Milestone: M4 | Release: R4 | Version: v0.4.0 | Tags: M4;tests;quality;pytest
Purpose: Prevent regressions as the tool evolves and is adopted by others.
Deliverables

Pytest configured; tests cover scoring + reporting helpers + at least one collector.
Tests/Validation

python -m pytest passes in clean environment.

17) T17 — Weekly runner script (PowerShell)

Milestone: M4 | Release: R4 | Version: v0.4.0 | Tags: M4;ops;script;automation
Purpose: Make operation repeatable for non-experts.
Deliverables

scripts/run_weekly.ps1 supports -Reports, -Dashboard, -Since, bind host/port

Does not generate CSVs unless requested.
Tests/Validation

Manual: run script with each switch combination; confirm outputs and dashboard starts.

18) T18 — Documentation pack + templates

Milestone: M4/M5 | Release: R5 | Version: v1.0.0 | Tags: M5;docs;templates;adoption
Purpose: Enable adoption and consistent usage across teams.
Deliverables

Docs: architecture, data model, operations

Templates: delivery-plan.md, ticket template in docs/tickets/
Tests/Validation

Manual: new engineer follows docs successfully; validate configs + run pipeline.

19) T19 — Adoption rollout kit

Milestone: M5 | Release: R5 | Version: v1.0.0 | Tags: M5;rollout;training;governance
Purpose: Ensure engineers actually use it and leaders can act on it.
Deliverables

Standard onboarding checklist for teams

“Support flags” definitions and expectations (non-punitive, coaching-focused)

Sample repo set + reporting cadence guidance
Tests/Validation

Pilot with two teams; confirm weekly usage and actionable outputs.

Demo Plan (milestone-based)
Demo #1 — M1 / R1 (end of Week 1 — <DATE>)

What is shown (live flow)

Show config formats and accepted scope/acceptance criteria.

Show DB schema and example snapshot JSON structure.
Artifacts

Screenshot of configs, schema, and a sample stored snapshot
Pass/Fail

Pass if scope is locked and schema supports planned fields without silent drops.

Demo #2 — M2 / R2 (end of Week 2 — <DATE>)

What is shown

Run: collect → score → persist → generate at least one CSV from DB.

Show one repo producing green/yellow/red with explanation.
Artifacts

Terminal logs, DB counts, generated CSV, python -m pytest output (if started)
Pass/Fail

Pass if end-to-end run works for minimal set and produces consistent outputs.

Demo #3 — M3 / R3 (end of Week 3 — <DATE>)

What is shown

Run against realistic scale definition (e.g., 30 repos).

Dashboard / portfolio view with filtering + tag/release columns.

Audit drilldown /audit with ✅/❌ hygiene signals.
Artifacts

Screenshots of dashboard views + a saved weekly CSV
Pass/Fail

Pass if leaders can triage “what’s risky and why” without manual wrangling.

Demo #4 — M4 / R4 (end of Week 4 — <DATE>)

What is shown

Reliability: retry/backoff behavior and clean failure summary.

Config validator catches common mistakes.

Weekly runner script produces reports on demand and starts dashboard.

Tests run cleanly.
Artifacts

Script output, validator output, pytest output, updated docs excerpt
Pass/Fail

Pass if operation is repeatable and safe for others to run.

Demo #5 — M5 / R5 (post-Week 4 — <DATE>)

What is shown

Onboarding a new repo/team using templates.

Show how support flags drive coaching/assistance, not punishment.
Artifacts

Completed delivery-plan/tickets templates + portfolio view with multiple teams
Pass/Fail

Pass if teams can adopt and leadership can take action weekly.