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

> **Note:** `exports/` is git-ignored. Do not commit CSV files.
<!-- /MANAGED:RUN -->

<!-- MANAGED:WEEKLY_SCRIPT -->
## Automated Weekly Pipeline (`scripts/run_weekly.ps1`)

The PowerShell script runs all four steps in sequence:

```powershell
# Auto-compute last Monday UTC
.\scripts\run_weekly.ps1

# Override the week start date
.\scripts\run_weekly.ps1 -Since 2026-02-10
```

Steps executed:
1. `repopulse db check` — verify connection
2. `repopulse snapshots run` — collect and score all repos
3. `repopulse report weekly --since $Since --out exports/weekly.csv`
4. `repopulse deepdive queue --out exports/deepdive_queue.csv`

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

<!-- MANAGED:OWNERSHIP_CHECKLIST -->
## Ownership Checklist

### Add a new repo
1. Edit `configs/repos.yaml` — add a new entry:
   ```yaml
   - url: "https://github.com/org/newrepo"
     owner: "org"
     name: "newrepo"
     dev_owner_name: "Owner Name"   # optional
     team: "platform"               # optional
   ```
2. Run `repopulse snapshots run` to collect and score immediately.
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
