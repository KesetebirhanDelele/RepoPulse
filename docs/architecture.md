# RepoPulse Architecture

<!-- MANAGED:OVERVIEW -->
## Overview

RepoPulse is a CLI-driven repo health monitoring tool. It collects signals from
GitHub APIs, scores each repo against configurable thresholds, persists results
to a SQL database (SQL Server or SQLite), and exports CSV reports for review.

Interaction is via the `repopulse` CLI, the `scripts/run_weekly.ps1` automation
script, or the optional web dashboard (`repopulse dashboard run`).
<!-- /MANAGED:OVERVIEW -->

<!-- MANAGED:COMPONENTS -->
## Components

### CLI (`app/app.py`)
Built with [Typer](https://typer.tiangolo.com/). Command groups:

| Command group | Key subcommands | Purpose |
|---|---|---|
| `repos` | `import`, `add` | Manage tracked repos |
| `snapshots` | `run` | Collect signals and score all repos |
| `report` | `weekly` | Generate weekly rollup CSV |
| `deepdive` | `queue` | Generate attention queue CSV |
| `db` | `check` | Verify DB connection and print table counts |
| `dashboard` | `run` | Start local dashboard server |

### Collectors (`app/collector/`)
Each collector enriches the signals dict for a single repo. All are optional
and independently enabled/disabled via `configs/signals.yaml`.

| Collector | Signal | Notes |
|---|---|---|
| `CommitsCollector` | `last_commit_at`, `commits_24h`, `commits_7d`, `top_files_24h` | Falls back to a single latest-commit fetch when `commits_7d` is empty |
| `ActionsCollector` | `ci_status`, `ci_conclusion`, `ci_updated_at` | 404 → `ci_status=none`; non-blocking |
| `ReleasesCollector` | `latest_tag`, `latest_release` | — |
| `ReadmeCollector` | *(stub — sets fields to `null`; not yet implemented)* | Placeholder for future README freshness signals |
| `TreeScanCollector` | `readme_present`, `tests_present`, `docs_missing`, `gitignore_present`, `env_not_tracked`, `claude_md_present` | Scans git tree + Contents API; `claude_md_present` checked independently so one failure cannot suppress other fields |

### Scoring Engine (`app/scoring/engine.py`)
Reads `configs/default.yaml` at runtime. Evaluates red/yellow/green rules and
churn risk rules against the collected signals dict. Returns a `RepoSnapshot`
Pydantic model.

### Storage (`app/storage/`)
SQLAlchemy 2.0. Supports any DB reachable via a `DB_URL` connection string.

| Class | Table | Purpose |
|---|---|---|
| `RepoStore` | `repos` | Tracked repo metadata |
| `RunStore` | `runs` | Per-run audit trail |
| `SnapshotStore` | `snapshots` | Latest scored snapshot per repo |

### Reporting (`app/reporting/`)
Pure Python; writes CSV files to `exports/` (git-ignored).

| Module | Output file | Contents |
|---|---|---|
| `csv_export.py` | `latest_snapshot.csv` | Flat snapshot after each run |
| `weekly.py` | `weekly.csv` | Rollup filtered by `--since` date |
| `deepdive.py` | `deepdive_queue.csv` | Red/yellow repos + risk flags |

### Dashboard (`app/dashboard/server.py`)
FastAPI server; server-rendered HTML only — no JavaScript frontend.

| Route | Purpose |
|---|---|
| `GET /` | Portfolio overview — RYG badge per repo, status/team filters, snapshot timestamp |
| `GET /manage` | Register public GitHub repos by URL; trigger snapshot runs from the browser |
| `POST /manage/register` | Upserts repos into the DB keyed on `(owner, name)`; returns Added/Updated/Invalid counts |
| `POST /run/snapshots` | Runs the collect → score → persist pipeline in-process; redirects to `/` with a summary banner |
| `GET /audit` | Per-repo file hygiene: README, tests, docs, .gitignore, CLAUDE.md, .env tracking |
| `GET /risks` | Risk heatmap — repos × risk flag categories with RYG severity cells |
| `GET /support` | Ownership & support rollup; team/dev-owner table + apps needing attention |
<!-- /MANAGED:COMPONENTS -->

<!-- MANAGED:DATA_FLOW -->
## Data Flow

```
  configs/repos.yaml          POST /manage/register (web UI)
         │                              │
         ▼                              ▼
  RepoStore.import_from_yaml()   _upsert_repo() → repos table
         │                              │
         └──────────────────────────────┘
                        │
                        ▼  repo_store.list_repos()
  For each repo:
    CommitsCollector → ActionsCollector → ReleasesCollector
    → ReadmeCollector → TreeScanCollector
    (signals dict enriched by each)
                        │
                        ▼
  ScoringEngine.score(signals)  ← configs/default.yaml
                        │
                        ▼
  SnapshotStore.upsert_snapshot()   →  snapshots table
  RunStore.finish_run()             →  runs table
                        │
                        ▼
  export_latest_snapshot_csv()  →  exports/latest_snapshot.csv
                        │
                        ▼ (on-demand)
  export_weekly_csv()           →  exports/weekly.csv
  export_deepdive_queue_csv()   →  exports/deepdive_queue.csv

  Dashboard (repopulse dashboard run):
    GET /   →  reads snapshots table  →  portfolio HTML
    GET /manage  →  reads repos table  →  manage HTML
    GET /audit   →  reads snapshots table  →  audit HTML
    GET /risks   →  reads snapshots table  →  heatmap HTML
    GET /support →  reads snapshots table  →  support HTML
```
<!-- /MANAGED:DATA_FLOW -->

<!-- MANAGED:CONFIG_DRIVEN -->
## Config-Driven Scoring

All scoring thresholds live in `configs/default.yaml`. No thresholds are
hardcoded in Python.

**`ryg_rules`** — evaluated top-down; first match wins:
- `red.any` — triggers RED if any condition matches (e.g. `no_commits_in_days_gte: 7`)
- `yellow.any` — triggers YELLOW if any condition matches
- `green.all` — repo is GREEN only if all conditions pass

**`churn_risk_rules`** — independent of RYG; produce `risk_flags` attached to
the snapshot. Repos with risk flags appear in the deepdive queue even if green.

**`configs/signals.yaml`** — controls which collectors run and their parameters
(e.g. `collection.actions.enabled`, `max_commit_details`).
<!-- /MANAGED:CONFIG_DRIVEN -->

<!-- MANAGED:EXTENDING -->
## Extending the System

**Add a collector:**
1. Create `app/collector/my_collector.py` with an `enrich(signals, signals_path)` method.
2. Add an enable flag under `collection.my_collector.enabled` in `configs/signals.yaml`.
3. Instantiate and append to the `collectors` list in `app/app.py`.

**Add a scoring rule:**
- Edit `ryg_rules` or `churn_risk_rules` in `configs/default.yaml`.
- Add a matching `_match_condition` branch in `app/scoring/engine.py` if the
  condition type is new.

**Add a report:**
1. Create `app/reporting/my_report.py`.
2. Register a new Typer command in `app/app.py`.
<!-- /MANAGED:EXTENDING -->
