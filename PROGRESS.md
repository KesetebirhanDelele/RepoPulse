# PROGRESS.md — RepoPulse Repository State Ledger

**Created:** 2026-05-29  
**Last Updated:** 2026-06-03  
**Repository Status:** Partially Implemented  
**Current Branch:** `feature/manage-page-ui`

---

## Project Overview

RepoPulse is a GitHub repository health monitoring tool. It collects signals from GitHub repos (commits, CI status, releases, docs, tree structure), scores them via a configurable engine, stores snapshots in a SQL database, and exposes a FastAPI dashboard with portfolio, audit, ownership, and repo management views.

---

## Current Phase: Phase 1 — Core Collection & Dashboard (Active)

---

## Known Architecture

| Layer | Location | Status |
|---|---|---|
| CLI entrypoint | `app/app.py` | Integrated |
| Settings / env loading | `app/settings.py` | Integrated |
| GitHub client | `app/github/github_client.py` | Integrated |
| Collectors (commits, actions, releases, readme, tree) | `app/collector/` | Integrated |
| Scoring engine | `app/scoring/engine.py` | Integrated |
| Storage (SQLAlchemy, SQLite/MSSQL) | `app/storage/` | Integrated |
| Dashboard (FastAPI + server-rendered HTML) | `app/dashboard/server.py` | Integrated |
| Reporting (CSV exports) | `app/reporting/` | Integrated |
| Config validation | `app/validate_configs.py` | Integrated |
| Directives | `/directives/` | **Not yet created** |
| Spec / requirements | `/spec/` | **Not yet created** |

### Signals collected per snapshot

| Signal | Source | Schema field |
|---|---|---|
| Commits (24h, 7d, top files) | `CommitsCollector` | `commits_24h`, `commits_7d`, `top_files_*` |
| CI status / conclusion | `ActionsCollector` | `ci_status`, `ci_conclusion` |
| Latest tag / release | `ReleasesCollector` | `latest_tag`, `latest_release` |
| README presence + freshness | `ReadmeCollector` | `readme_present`, `readme_updated_within_7d`, etc. |
| Tests present | `TreeScanCollector` | `tests_present` |
| Docs missing | `TreeScanCollector` | `docs_missing` |
| .gitignore present | `TreeScanCollector` | `gitignore_present` |
| .env not tracked | `TreeScanCollector` | `env_not_tracked` |
| CLAUDE.md present | `TreeScanCollector` | `claude_md_present` |
| PROGRESS.md present | `TreeScanCollector` | `progress_md_present` |

---

## CLAUDE.md Compliance Gap Analysis (as of 2026-06-03)

This section documents gaps between what CLAUDE.md requires and the current repository state.

| Requirement | CLAUDE.md Section | Current State | Gap |
|---|---|---|---|
| `/directives/` folder with SOPs | System Layers — Layer 1 | Not created | **Critical gap** — no behavioral runbooks exist |
| `/spec/` requirements file | Session Startup Rule | Not created | No formal deliverable specification on disk |
| Layer separation: no orchestration in execution scripts | Never mix layers | `_run_snapshots_pipeline()` lives inside `app/dashboard/server.py` | Borderline — web layer, not execution script; acceptable for MVP |
| Unit tests for all non-trivial execution logic | Unit Testing | Collectors (tree_scan, actions, commits, readme) have no unit tests | **Gap** — coverage is partial |
| Integration test scaffold | Integration Testing | Not present | **Gap** |
| E2E / Playwright tests | End-to-End & UI Testing | Not present | **Gap** |
| One-command test execution | Intern Safety Rules | `pytest` from root works for existing tests | Partially met |
| No secrets in repo | Intern Safety Rules | `.env` not tracked (confirmed by `env_not_tracked` signal design) | Met |

**Layer boundary note:** `_run_snapshots_pipeline()` in `app/dashboard/server.py` (line 868) performs orchestration (loops over collectors, scores, persists). CLAUDE.md states orchestration belongs in Layer 2 (Claude) or Layer 3 (execution scripts), not the web layer. This is an architectural debt item; it works correctly but violates the stated separation for a production-grade system.

---

## Implementation Status

### Completed
- Full collector pipeline (commits, CI, releases, README, tree scan)
- `progress_md_present` and `claude_md_present` signals in `TreeScanCollector`, `RepoSnapshot` schema, and `ScoringEngine`
- Scoring engine with configurable signals YAML and RYG rule evaluation
- SQLite and SQL Server storage backends
- Dashboard: portfolio view, audit view (with PROGRESS.md and CLAUDE.md columns), ownership/support view, manage repos page
- Repo active/inactive toggle (Deactivate/Reactivate buttons on manage page)
- Per-repo edit page (`/manage/edit`) for URL, team, dev_owner_name
- Unsnapshotted active repos shown with "pending" RYG status in portfolio view
- Snapshot generation via web UI trigger (`/run/snapshots`)
- CSV export (latest snapshot, weekly, deepdive queue)
- Config validation CLI command

### Partially Implemented
- **Directives layer** — `/directives/` folder does not exist; no SOPs documented
- **Test coverage** — unit tests exist for scoring engine, reporting helpers, releases collector; `TreeScanCollector`, `ActionsCollector`, `CommitsCollector`, `ReadmeCollector`, and dashboard routes have no tests

### Known Gaps
- No directives for any workflow
- No integration tests
- No E2E / Playwright tests
- No unit test for `Settings` env reloading behavior
- No unit tests for `TreeScanCollector` (including `progress_md_present` signal)
- No unit tests for dashboard routes
- `_run_snapshots_pipeline()` mixes orchestration into the web layer (`server.py`)
- No `spec/` folder or formal requirements document on disk

---

## Capability Maturity

| Capability | Maturity | Notes |
|---|---|---|
| Signal collection pipeline | Integrated | All collectors wired; no unit tests for tree/actions/commits/readme collectors |
| Scoring engine (RYG) | Tested | `test_scoring_engine.py` present; no integration test |
| Storage (SQLite/MSSQL) | Integrated | No test for db init, upsert behavior |
| Dashboard — portfolio view | Integrated | Pending RYG status, active/all filter working; no route tests |
| Dashboard — audit view | Integrated | Shows PROGRESS.md + CLAUDE.md columns; no route tests |
| Dashboard — ownership/support view | Integrated | Team rollup + attention list; no route tests |
| Dashboard — manage repos | Integrated | Register, edit, toggle active; no route tests |
| CSV export / reporting | Tested | `test_reporting_helpers.py` present |
| Config validation | Integrated | `validate_configs.py` present; no unit test |
| Directives / SOPs | Planned | `/directives/` folder does not exist |
| Integration tests | Planned | Not started |
| E2E / UI tests | Planned | Not started |

---

## Change Log

---

### Entry 001 — 2026-05-29

**Phase:** Phase 1  
**Status:** Integrated (behavioral fix)

#### What Changed

- **`app/settings.py` line 22** — Removed `if key not in os.environ` guard in `_load_dotenv`.  
  Previously, once an env key was set in `os.environ` (on first `Settings()` instantiation), subsequent instantiations would never update it even if `.env` changed. Now `.env` always wins on each `Settings()` call.
- **Impact:** Dashboard server picks up `.env` changes on the next HTTP request without any restart. All CLI commands (which already create fresh processes) are unaffected.

#### Validation

- Change reviewed manually against `app/dashboard/server.py` — confirmed `Settings()` is instantiated per-request, not as a module-level singleton.
- **No automated test written yet** — this is a known gap.

#### Risks / Limitations

- `.env` now takes precedence over OS-level environment variables. Previously, OS env vars silently shadowed `.env`. This is the correct behavior for this project but is a behavioral change.
- No test guards against regression (e.g., future re-introduction of the skip guard).

#### Next Actions

- [ ] Write unit test: `Settings()` re-reads updated `.env` values on re-instantiation
- [ ] Create `/directives/` folder with at least one SOP (e.g., `env-configuration.md`)
- [ ] Add integration test scaffold

---

### Entry 002 — 2026-05-29

**Phase:** Phase 1  
**Commit:** `4bc22a3`  
**Status:** Integrated (dashboard enhancement)

#### What Changed

- **`app/dashboard/server.py`** — Added support for active repos with no snapshots yet:
  - New SQL query `_UNSNAPSHOTTED_ACTIVE_SQL` returns active repos not present in `snapshots` table.
  - `_load_rows()` now appends these repos with `status_ryg = "pending"` when no RYG filter is active.
  - `_RYG_ORDER` extended with `"pending": 3` so pending repos sort after green.
  - Portfolio counter bar shows "Pending: N" chip when pending repos exist.
  - New `show` query param (`active` / `all`) added to the portfolio filter form, allowing inactive repos to be shown alongside active ones.
  - `_FILTER_FORM` and `_render_html()` updated with the show-filter select.

#### Validation

- Manual review of SQL and Python logic confirms the `NOT EXISTS` guard correctly excludes repos that already have at least one snapshot.
- No automated tests for dashboard routes — this is a known gap.

#### Risks / Limitations

- Pending repos carry no signal data; any score-dependent filter hides them (by design).
- No test verifies that the pending row is not duplicated if a snapshot is later added.

#### Next Actions

- [ ] Add route test for `GET /` covering pending-repo rendering
- [ ] Verify sort order (red → yellow → green → pending) with a test fixture

---

### Entry 003 — 2026-05-29

**Phase:** Phase 1  
**Commit:** `1ac8d8b`  
**Status:** Governance update (no executable change)

#### What Changed

- **`CLAUDE.md`** — Tightened the `PROGRESS.md` Creation Rule:
  - Added explicit prohibition on overwriting or resetting an existing `PROGRESS.md`.
  - Clarified that creation is a one-time bootstrapping action per repository lifetime.
  - Added the Session Startup Rule requiring a check for existence before any creation attempt.

#### Validation

- Documentation-only change; no code affected.

#### Risks / Limitations

- None.

#### Next Actions

- None for this entry.

---

### Entry 004 — 2026-06-01

**Phase:** Phase 1  
**Commit:** `20f6763`  
**Status:** Integrated (new signal + schema + dashboard column)

#### What Changed

- **`app/collector/tree_scan.py`** — Added `progress_md_present` detection.  
  - Uses the git tree blob list (case-insensitive match on `progress.md`) when available; falls back to three-variant Contents API probe (`PROGRESS.md`, `progress.md`, `Progress.md`).  
  - Pattern mirrors the existing `claude_md_present` implementation for consistency.
  - `signals.update(...)` block now includes `"progress_md_present": progress_md_present`.

- **`app/schemas.py`** — Added `progress_md_present: Optional[bool] = None` to `RepoSnapshot` (hygiene signals block, line 73).

- **`app/scoring/engine.py`** — Added `progress_md_present=signals.get("progress_md_present")` to the `RepoSnapshot(...)` constructor in `ScoringEngine.score()` (line 76).

- **`app/dashboard/server.py`** — Two changes:
  - `_load_audit_row()` now reads `"progress_md_present"` from the snapshot JSON (line 458).
  - `_render_audit_html()` audit table header and row updated to include a "PROGRESS.md" column with ✅/❌ rendering (lines 481–492).

#### Validation

- Manual code review confirms the signal flows end-to-end: collector → schema → engine → storage (via JSON blob) → dashboard audit column.
- **No automated test written** for `progress_md_present` in `TreeScanCollector` — known gap.
- No test verifies the audit page renders the column correctly.

#### Risks / Limitations

- The detection relies on the git tree being non-truncated for large repos; truncated trees fall back to the Contents API (correct fail-open behavior, same as `claude_md_present`).
- Existing snapshot rows in the DB will have `progress_md_present = null` until re-snapshotted.

#### Next Actions

- [ ] Write unit test for `TreeScanCollector.enrich()` verifying `progress_md_present` in both tree-path and Contents-API fallback paths
- [ ] Write unit test for `ScoringEngine.score()` passing `progress_md_present=True/False`

---

## Testing Status

| Test file | Coverage | Status |
|---|---|---|
| `tests/test_scoring_engine.py` | Scoring logic (RYG evaluation, churn rules) | Present |
| `tests/test_reporting_helpers.py` | Reporting helpers (CSV export) | Present |
| `tests/test_releases_collector.py` | Releases collector | Present |
| `TreeScanCollector` — all signals | `app/collector/tree_scan.py` | **Missing** |
| `progress_md_present` flow | `tree_scan.py` → `engine.py` → `server.py` | **Missing** |
| `Settings` env reload | `app/settings.py` | **Missing** |
| Dashboard routes | `app/dashboard/server.py` | **Missing** |
| `CommitsCollector` | `app/collector/commits.py` | **Missing** |
| `ActionsCollector` | `app/collector/actions.py` | **Missing** |
| `ReadmeCollector` | `app/collector/readme.py` | **Missing** |

---

## Next Recommended Actions

**Priority 1 — Close critical test gaps (required by CLAUDE.md)**
1. Write unit test for `TreeScanCollector.enrich()` covering `progress_md_present` and `claude_md_present` (tree path + Contents API fallback paths)
2. Write unit test for `Settings` env reload behavior (re-instantiation reads updated `.env`)
3. Scaffold dashboard route tests with a test SQLite fixture (`GET /`, `/audit`, `/manage`)

**Priority 2 — Directives layer (required by CLAUDE.md)**
4. Create `/directives/` folder
5. Write `directives/env-configuration.md` SOP covering `.env` precedence behavior and reload contract
6. Write `directives/snapshot-pipeline.md` covering collection, scoring, and storage steps

**Priority 3 — Architecture debt**
7. Extract `_run_snapshots_pipeline()` from `server.py` into an execution script (e.g., `execution/run_pipeline.py`) to restore CLAUDE.md layer separation
8. Create `spec/requirements.md` to formalize the deliverable on disk

**Priority 4 — Test completeness**
9. Add unit tests for `CommitsCollector`, `ActionsCollector`, `ReadmeCollector`
10. Add integration test scaffold (test DB, mock GitHub API responses)
