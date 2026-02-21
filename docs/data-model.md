# RepoPulse Data Model

<!-- MANAGED:TABLES -->
## Database Tables

All tables are created via `app/storage/sa.py` using SQLAlchemy metadata.
The target database is controlled by `DB_URL` in `.env`.

### `repos`
Tracked repository registry.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK (autoincrement) | — |
| `url` | Text | Full GitHub URL |
| `owner` | String(255) | GitHub org or user |
| `name` | String(255) | Repository name |
| `dev_owner_name` | String(255) | Human-readable owner label |
| `team` | String(255) | Team/squad label |

### `runs`
One row per `repopulse snapshots run` invocation.

| Column | Type | Notes |
|---|---|---|
| `run_id` | String(36) PK | UUID |
| `started_at` | String(64) | ISO 8601 UTC |
| `finished_at` | String(64) | ISO 8601 UTC |
| `failures_json` | Text | JSON array of `{repo, error}` |
| `outputs_json` | Text | JSON dict of output file paths |
| `api_mode` | String(20) | `"token"` or `"no-token"` |
| `config_used_path` | String(512) | Path to default.yaml used |
| `config_hash` | String(64) | SHA-256 of config file |
| `signals_used_path` | String(512) | Path to signals.yaml used |
| `signals_hash` | String(64) | SHA-256 of signals file |
| `repos_used_path` | String(512) | Path to repos.yaml used |
| `repos_hash` | String(64) | SHA-256 of repos file |
| `scoring_version` | String(50) | From `scoring_version` in default.yaml |
| `db_path` | String(512) | DB path/URL recorded at runtime |

### `snapshots`
Latest scored snapshot per repo. Composite PK = `(run_id, owner, name)`.

| Column | Type | Notes |
|---|---|---|
| `run_id` | String(36) PK | References the run that produced this row |
| `owner` | String(255) PK | GitHub org or user |
| `name` | String(255) PK | Repository name |
| `captured_at` | String(64) | ISO 8601 UTC — used for latest-row selection |
| `snapshot_json` | Text | Full `RepoSnapshot` serialised as JSON |

> The `SnapshotStore` upserts by deleting then re-inserting on the same
> `(run_id, owner, name)` key, so each repo has exactly one row per run.
> Reporting queries use `MAX(captured_at) GROUP BY owner, name` to get the
> most recent snapshot across all runs.
<!-- /MANAGED:TABLES -->

<!-- MANAGED:SNAPSHOT_JSON -->
## `snapshot_json` Schema

The `snapshot_json` column stores the full `RepoSnapshot` Pydantic model
serialised via `.model_dump()` + `json.dumps(..., default=str)`.

Key fields used by reporting:

```
{
  "run_id": "uuid",
  "captured_at": "2026-02-20T10:00:00+00:00",
  "repo": {
    "url": "https://github.com/org/repo",
    "owner": "org",
    "name": "repo",
    "dev_owner_name": "Jane Smith",
    "team": "platform"
  },
  "default_branch": "main",
  "last_commit_at": "2026-02-18T14:32:00+00:00",
  "commits_24h": 3,
  "commits_7d": 12,
  "top_files_24h": ["src/main.py", "tests/test_api.py"],
  "top_files_7d": ["src/main.py"],
  "ci_status": "success",          // "success"|"failure"|"none"|"unknown"
  "ci_conclusion": "success",
  "ci_updated_at": "2026-02-20T09:00:00+00:00",
  "latest_tag": "v1.2.0",
  "latest_release": "v1.2.0",
  "required_files_missing": [],
  "required_globs_missing": [],
  "status_ryg": "green",           // "red"|"yellow"|"green"
  "status_explanation": "Meets configured freshness/CI/docs criteria.",
  "risk_flags": [
    {
      "id": "high_commits_no_release",
      "label": "churn_risk",
      "severity": "yellow",
      "message": "High commit volume without delivery marker."
    }
  ],
  "evidence": []
}
```
<!-- /MANAGED:SNAPSHOT_JSON -->

<!-- MANAGED:FIELD_MEANINGS -->
## Field Meanings

### `status_ryg`
The overall health colour evaluated by the scoring engine against `configs/default.yaml`.

| Value | Meaning |
|---|---|
| `red` | Repo is stale or has a failing CI — needs immediate attention |
| `yellow` | Repo is slowing down or missing required docs |
| `green` | Repo meets all configured freshness and CI criteria |

Default thresholds (overridable in `default.yaml`):
- **RED**: no commits in ≥ 7 days, OR CI conclusion is `failure`/`cancelled`/`timed_out`
- **YELLOW**: no commits in ≥ 2 days, OR missing any required file
- **GREEN**: no commits in ≤ 2 days AND CI is success or absent (`ci_ok_or_missing_allowed`)

### `ci_status`
Normalised CI state derived from the latest GitHub Actions workflow run.

| Value | Source |
|---|---|
| `success` | `conclusion == "success"` |
| `failure` | `conclusion` in failure set (failure, cancelled, timed_out, …) |
| `unknown` | Run is queued/in_progress, or API error |
| `none` | Repo has no GitHub Actions workflows, or endpoint returned 404 |

CI is **optional**. `ci_status=none` does not penalise a repo by default
(`thresholds.ci.yellow_if_missing: false`).

### `risk_flags`
A list of churn/risk rule matches, each with `id`, `label`, `severity`, and
`message`. Risk flags are independent of the RYG colour. A green repo can still
appear in the deepdive queue if it has active risk flags.

Example rule IDs defined in `default.yaml`:
- `high_commits_no_release` — high commit volume but no recent tag/release
- `refactor_heavy` — commit mix is predominantly refactor/chore
- `contracts_churn_no_version` — contracts changing without a version marker
<!-- /MANAGED:FIELD_MEANINGS -->

<!-- MANAGED:REPORTING_MAPPING -->
## Reporting Column Mapping

### `exports/weekly.csv`
Produced by `repopulse report weekly --since YYYY-MM-DD`.

| CSV column | Source in `snapshot_json` |
|---|---|
| `week_start` | `--since` argument |
| `owner` / `name` | `repo.owner` / `repo.name` (also from DB row) |
| `team` | `repo.team` |
| `dev_owner_name` | `repo.dev_owner_name` |
| `captured_at` | DB `snapshots.captured_at` |
| `commits_7d` | `commits_7d` |
| `last_commit_at` | `last_commit_at` |
| `ci_status` | `ci_status` |
| `latest_tag` | `latest_tag` |
| `latest_release` | `latest_release` |
| `top_files_7d` | `top_files_7d` joined with `;` |
| `status_ryg` | `status_ryg` |
| `status_explanation` | `status_explanation` |
| `risk_flags` | `risk_flags[].id` joined with `;` |

Sorted: red → yellow → green, then owner → name.

### `exports/deepdive_queue.csv`
Produced by `repopulse deepdive queue`. Only includes repos where
`status_ryg` is `red` or `yellow`, OR `risk_flags` is non-empty.

| CSV column | Source |
|---|---|
| `owner` / `name` | DB row / `repo.*` |
| `team` / `dev_owner_name` | `repo.team` / `repo.dev_owner_name` |
| `status_ryg` | `status_ryg` |
| `reason` | Pipe-joined: `status_explanation` \| `CI: <ci_status>` \| `Missing docs: N` \| `Risks: <ids>` |
| `captured_at` | DB `snapshots.captured_at` |

Sorted: red → yellow, then owner → name.
<!-- /MANAGED:REPORTING_MAPPING -->
