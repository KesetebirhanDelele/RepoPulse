# RepoPulse Operations

<!-- MANAGED:ENV -->
## Environment Setup (`.env`)

Create a `.env` file in the project root. **This file is git-ignored and must
never be committed.**

### SQL Server with Windows Authentication (recommended for on-prem)
```
DB_URL=mssql+pyodbc://server/database?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
```

### SQL Server with SQL Authentication
```
DB_URL=mssql+pyodbc://username:password@server/database?driver=ODBC+Driver+17+for+SQL+Server
```

### SQLite (local dev / no SQL Server)
```
DB_URL=sqlite:///data/repopulse.sqlite3
```
If `DB_URL` is not set, SQLite is used by default and `data/` is created automatically.

### GitHub Token (optional but recommended)
```
GITHUB_TOKEN=ghp_yourpersonalaccesstoken
```
Without a token, GitHub's unauthenticated rate limit applies (60 req/hr).
With a token the limit is 5,000 req/hr. For repos with many commits or
detailed file tracking, a token is strongly recommended.
<!-- /MANAGED:ENV -->

<!-- MANAGED:RUN -->
## Running RepoPulse

### First-time setup
```bash
pip install -e .
repopulse db check      # verify connection and create tables
```

### Verify DB connection
```bash
repopulse db check
```
Prints the (redacted) DB URL and row counts for `repos`, `runs`, `snapshots`.

### Collect snapshots
```bash
repopulse snapshots run
```
Uses `configs/repos.yaml`, `configs/default.yaml`, and `configs/signals.yaml`.
Writes `exports/latest_snapshot.csv` on completion.

### Weekly rollup report
```bash
repopulse report weekly --since 2026-02-17 --out exports/weekly.csv
```
Queries all snapshots captured on or after `--since`, picks the latest per repo,
and writes `exports/weekly.csv` sorted by status (red first).

### Deep-dive queue
```bash
repopulse deepdive queue --out exports/deepdive_queue.csv
```
Writes repos that are red/yellow or have active risk flags, with a
human-readable reason string.

### Start the web dashboard
```bash
repopulse dashboard run
repopulse dashboard run --host 0.0.0.0 --port 9000
```
Starts a local FastAPI server (default `http://127.0.0.1:8000`).
Blocks until Ctrl+C. Available pages:

| URL | Purpose |
|---|---|
| `/` | Portfolio overview — RYG status, status/team filters, snapshot timestamp |
| `/manage` | Register public GitHub repos by URL; trigger snapshot runs in-browser |
| `/audit?owner=ORG&name=REPO` | Per-repo file hygiene (README, tests, docs, .gitignore, CLAUDE.md, .env) |
| `/risks` | Risk heatmap — repos × risk flag categories |
| `/support` | Ownership & support rollup; apps needing attention |

> **Note:** `exports/` is git-ignored. Do not commit CSV files.
<!-- /MANAGED:RUN -->

<!-- MANAGED:WEEKLY_SCRIPT -->
## Automated Weekly Pipeline (`scripts/run_weekly.ps1`)

Always runs: `repopulse db check` → `repopulse snapshots run`.
Optional flags control CSV generation and the dashboard server.

### Switch reference

| Switch | Default | Effect |
|---|---|---|
| `-Since <date>` | last Monday UTC | Override the week-start date for report queries |
| `-Reports` | off | Generate `exports/weekly.csv` and `exports/deepdive_queue.csv` |
| `-Dashboard` | off | Start the web dashboard after snapshots (blocks until Ctrl+C) |
| `-BindHost <host>` | `127.0.0.1` | Dashboard listen address (used only with `-Dashboard`) |
| `-BindPort <port>` | `8000` | Dashboard listen port (used only with `-Dashboard`) |

### Usage patterns

```powershell
# Daily: snapshots only
.\scripts\run_weekly.ps1

# Weekly (Monday): snapshots + CSV reports
.\scripts\run_weekly.ps1 -Reports

# Ad-hoc dashboard review after snapshots
.\scripts\run_weekly.ps1 -Dashboard

# Full weekly pipeline with custom week start and dashboard
.\scripts\run_weekly.ps1 -Since 2026-02-13 -Reports -Dashboard -BindHost 127.0.0.1 -BindPort 8000
```

`-Reports` controls whether CSVs are written. `exports/` is git-ignored — do not commit CSV files.

The script uses `$ErrorActionPreference = "Stop"`, so any failure aborts the
pipeline immediately. The `exports/` directory is created if missing.

**Scheduling:** Run via Windows Task Scheduler or manually each Monday morning.
<!-- /MANAGED:WEEKLY_SCRIPT -->

<!-- MANAGED:TROUBLESHOOTING -->
## Troubleshooting

### GitHub 403 / rate limit exceeded
- Symptom: collector raises HTTP 403; repo shows `ci_status=unknown` or fails entirely.
- Cause: Unauthenticated requests exhausted (60/hr), or secondary rate limit hit.
- Fix: Set `GITHUB_TOKEN` in `.env`. The `GitHubClient` auto-retries once after
  sleeping until the `X-RateLimit-Reset` time (capped at 60s).

### ODBC Driver error on SQL Server connection
- Symptom: `pyodbc.InterfaceError: ('IM002', …)` or driver not found.
- Cause: Wrong driver name in `DB_URL`.
- Fix: Check installed ODBC drivers via `odbcad32.exe` or:
  ```powershell
  Get-OdbcDriver | Select-Object Name
  ```
  Use `ODBC Driver 17 for SQL Server` or `ODBC Driver 18 for SQL Server` as appropriate.
  For Driver 18, you may also need `TrustServerCertificate=yes` in the connection string.

### SQL Server login error 18456
- Symptom: `Login failed for user '...'` (error 18456).
- Cause: SQL auth credentials wrong, or SQL auth not enabled on the server.
- Fix: Use `trusted_connection=yes` for Windows auth, or verify the SQL login
  credentials. Confirm SQL Server is configured to allow Mixed Mode auth if
  using SQL auth.

### `repos.yaml` not found / no repos imported
- Symptom: `snapshots run` completes immediately with 0 snapshots.
- Cause: `configs/repos.yaml` is missing or the path passed to `--repos` is wrong.
- Fix: Ensure `configs/repos.yaml` exists and follows the flat list format:
  ```yaml
  - url: "https://github.com/org/repo"
    owner: "org"
    name: "repo"
  ```

### All repos show `no_commits_in_days` as very high / unexpected red
- Symptom: Repos known to be active still score red for staleness.
- Cause: When `commits_7d` is empty, the collector makes one additional call to
  fetch the single latest commit. If that call fails or returns empty, `last_commit_at`
  stays `None`, and the scoring engine treats `None` as "no commit timestamp
  available" → immediate red.
- Fix: Verify the GitHub token has read access to the repo. Check `failures_json`
  in the `runs` table for per-repo errors.
<!-- /MANAGED:TROUBLESHOOTING -->

<!-- MANAGED:AUDIT_EXTENSION -->
## Extending File Audit: Adding a New Dashboard Audit Column

Follow this checklist whenever you want to add a new boolean hygiene field
(e.g. `claude_md_present`) to the per-repo audit page.

### Checklist

**1. Collector — compute the signal and write it into `signals`**

In `app/collector/tree_scan.py` (or the relevant collector), compute the value
and add it to the `signals.update({...})` dict:

```python
try:
    my_field = bool(self._exists(owner, name, "some-file"))
except Exception:
    my_field = False

signals.update({
    ...,
    "my_field": my_field,
})
```

Always use a standalone `try/except` so one field's failure cannot suppress
the others. Wrap with `bool()` so the result is never `None`.

**2. Schema — declare the field on `RepoSnapshot`**

In `app/schemas.py`, add the field under `# Hygiene signals`:

```python
my_field: Optional[bool] = None
```

Without this, Pydantic silently drops the key during serialisation and it
will never appear in `snapshot_json`.

**3. Snapshot build / scoring — pass the value through**

In `app/scoring/engine.py`, inside `ScoringEngine.score()`, add the field to
the `RepoSnapshot(...)` constructor call alongside the other hygiene fields:

```python
my_field=signals.get("my_field"),
```

This is the bridge between raw signal dicts and the persisted JSON blob.

**4. Dashboard — render ✅ / ❌ in the audit page**

In `app/dashboard/server.py`:

- `_load_audit_row`: add the key to the returned dict:
  ```python
  "my_field": snap.get("my_field", False),
  ```
- `_render_audit_html`: add a `<th>` to `audit_header` and a `<td>` to
  `audit_row`:
  ```python
  "<th>My Field</th>"
  f"<td>{_bool_cell(row['my_field'])}</td>"
  ```

**5. Tests (recommended)**

Add a unit test in `tests/` that:
- Constructs a snapshot dict with the new key set to `True` / `False`.
- Calls the render/load helper and asserts the correct ✅ / ❌ cell appears.

### Debug symptoms

| Symptom | Most likely cause |
|---|---|
| Key absent from `snapshot_json` entirely | Schema field missing in `app/schemas.py` (Pydantic drops unknown extras) |
| Key present in JSON but value is `null` | `app/scoring/engine.py` didn't pass it to `RepoSnapshot(...)` (falls back to `None` default) |
| Key is `false` when you expect `true` | Collector logic wrong, API path incorrect, or a cached old snapshot is being read |
| ❌ shown on audit page for a repo that has the file | Old snapshot in DB — re-run `repopulse snapshots run` to collect a fresh one |

<!-- /MANAGED:AUDIT_EXTENSION -->

<!-- MANAGED:OWNERSHIP_CHECKLIST -->
## Ownership Checklist

### Add a new repo

**Option A — web UI (recommended):**
1. Open `http://127.0.0.1:8000/manage` with the dashboard running.
2. Paste one or more public GitHub URLs (one per line, `.git` suffix accepted).
3. Enter an optional team label and click **Register repos**.
4. Click **Generate snapshots** (or run `repopulse snapshots run`) to collect immediately.
5. Verify the repo appears on the portfolio page or in `exports/latest_snapshot.csv`.

**Option B — YAML import:**
1. Edit `configs/repos.yaml` — add a new entry:
   ```yaml
   - url: "https://github.com/org/newrepo"
     owner: "org"
     name: "newrepo"
     dev_owner_name: "Owner Name"   # optional
     team: "platform"               # optional
   ```
2. Run `repopulse snapshots run` (which re-imports the YAML into the DB) to collect and score immediately.
3. Verify the repo appears in `exports/latest_snapshot.csv`.

### Rotate the GitHub token
1. Generate a new fine-grained or classic PAT with `repo` read scope.
2. Update `GITHUB_TOKEN` in `.env`.
3. Run `repopulse db check` to confirm the connection still works (unrelated to
   the token, but a good smoke test).
4. Run `repopulse snapshots run` to confirm collectors succeed.

### Verify everything is working
```bash
repopulse db check
```
Expected output example:
```
db_url:      mssql+pyodbc://user:***@server/db?...
repos:       3
runs:        12
snapshots:   36
```
If `snapshots` count is 0 after a run, check `failures_json` in the `runs` table
for errors on individual repos.
<!-- /MANAGED:OWNERSHIP_CHECKLIST -->
