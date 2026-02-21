# RepoPulse
Track Sprint Status

## Runbook

### Prerequisites
- Python 3.11+
- Access to SQL Server (or SQLite for local dev)
- GitHub token optional but recommended (avoids rate limits)

### Setup
Create a `.env` file in the project root (git-ignored — never commit it):

```
DB_URL=mssql+pyodbc://server/database?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
GITHUB_TOKEN=ghp_yourtoken
```

Install dependencies and run once to create tables:

```bash
pip install -e .
repopulse db check
```

### Common Commands

```bash
# Verify DB connection and show table counts
repopulse db check

# Collect snapshots for all repos in configs/repos.yaml
repopulse snapshots run

# Weekly rollup report (since a given Monday)
repopulse report weekly --since 2026-02-17 --out exports/weekly.csv

# Deep-dive queue (red/yellow repos and those with risk flags)
repopulse deepdive queue --out exports/deepdive_queue.csv
```

### Weekly Runner Script (PowerShell)

```powershell
# Snapshots only (DB check + collect)
.\scripts\run_weekly.ps1

# Snapshots + CSV reports
.\scripts\run_weekly.ps1 -Reports

# Start dashboard after snapshots (blocks until Ctrl+C)
.\scripts\run_weekly.ps1 -Dashboard

# Full run: custom week start, reports, dashboard on custom address
.\scripts\run_weekly.ps1 -Since 2026-02-13 -Reports -Dashboard -BindHost 127.0.0.1 -BindPort 8000
```

Dashboard mode starts the web server and blocks until Ctrl+C.

### Running Tests

Use the same interpreter as the app to avoid version mismatches (e.g. 3.11 vs 3.12) when multiple Pythons are installed:

```bash
python -m pytest
```

### Adding Repos
Edit `configs/repos.yaml`:

```yaml
repos:
  - url: https://github.com/org/repo
    owner: org
    name: repo
    dev_owner_name: Jane Smith   # optional
    team: platform               # optional
```

### Notes
- CI is optional. Repos without GitHub Actions show `ci_status=none` and are not penalised.
- "No commits in 7 days" is treated as **red** (stale). The collector fetches the last commit date even for quiet repos.
