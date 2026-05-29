# PROGRESS.md — RepoPulse Repository State Ledger

**Created:** 2026-05-29  
**Repository Status:** Partially Implemented  

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

---

## Implementation Status

### Completed
- Full collector pipeline (commits, CI, releases, README, tree scan)
- Scoring engine with configurable signals YAML
- SQLite and SQL Server storage backends
- Dashboard: portfolio view, audit view, ownership/support view, manage repos page
- Repo active/inactive toggle
- Snapshot generation via web UI trigger
- CSV export (latest snapshot, weekly, deepdive queue)
- Config validation CLI command

### Partially Implemented
- **Directives layer** — `/directives/` folder does not exist; no SOPs documented yet
- **Test coverage** — unit tests exist for scoring engine, reporting helpers, releases collector; integration and E2E tests not present

### Known Gaps
- No directives for any workflow
- No integration tests
- No E2E / Playwright tests
- No test for `Settings` env reloading behavior (see Change Log below)
- `PROGRESS.md` not present until this session (now bootstrapped)

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
- **No automated test written yet** — this is a known gap (see Next Actions).

#### Risks / Limitations

- `.env` now takes precedence over OS-level environment variables. Previously, OS env vars silently shadowed `.env`. This is the correct behavior for this project but is a behavioral change.
- No test guards against regression (e.g., future re-introduction of the skip guard).

#### Next Actions

- [ ] Write unit test: `Settings()` re-reads updated `.env` values on re-instantiation
- [ ] Create `/directives/` folder with at least one SOP (e.g., `env-configuration.md`)
- [ ] Add integration test scaffold

---

## Testing Status

| Test file | Coverage | Status |
|---|---|---|
| `tests/test_scoring_engine.py` | Scoring logic | Present |
| `tests/test_reporting_helpers.py` | Reporting helpers | Present |
| `tests/test_releases_collector.py` | Releases collector | Present |
| Settings env reload | `app/settings.py` | **Missing** |
| Dashboard routes | `app/dashboard/server.py` | **Missing** |
| Collector integration | `app/collector/` | **Missing** |

---

## Next Recommended Actions

1. Write missing unit test for `Settings` env reload behavior
2. Create `/directives/` folder and document at least the env configuration SOP
3. Scaffold integration test for dashboard routes
4. Establish one-command test execution (`pytest` from repo root)
