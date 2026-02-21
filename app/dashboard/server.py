"""Minimal server-rendered HTML dashboard backed by SQL Server snapshots."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from app.settings import Settings
from app.storage.sa import get_engine

# ---------------------------------------------------------------------------
# SQL: latest snapshot per (owner, name)
# ---------------------------------------------------------------------------

_LATEST_SQL = text("""
    SELECT s.owner, s.name, s.captured_at, s.snapshot_json
    FROM snapshots s
    INNER JOIN (
        SELECT owner, name, MAX(captured_at) AS max_cap
        FROM snapshots
        GROUP BY owner, name
    ) latest
        ON  s.owner       = latest.owner
        AND s.name        = latest.name
        AND s.captured_at = latest.max_cap
    ORDER BY s.owner, s.name
""")

# ---------------------------------------------------------------------------
# RYG badge colours
# ---------------------------------------------------------------------------

_RYG_COLOURS = {
    "red":    ("#c0392b", "#fff"),
    "yellow": ("#f39c12", "#000"),
    "green":  ("#27ae60", "#fff"),
}

_RYG_ORDER = {"red": 0, "yellow": 1, "green": 2}


def _badge(status: str) -> str:
    bg, fg = _RYG_COLOURS.get(status, ("#888", "#fff"))
    label = status.upper() if status else "?"
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:3px;font-weight:bold;font-size:0.85em">{label}</span>'
    )


def _esc(value: Any) -> str:
    """HTML-escape a value for safe inline display."""
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _days_since(last_commit_str: str) -> int | None:
    """Return integer days between last_commit_str (ISO 8601) and now UTC, or None on parse failure."""
    if not last_commit_str:
        return None
    try:
        dt = datetime.fromisoformat(last_commit_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - dt).days)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_rows(status_filter: str, team_filter: str) -> list[dict[str, Any]]:
    engine = get_engine(Settings().db_url)
    rows: list[dict[str, Any]] = []

    with engine.connect() as conn:
        result = conn.execute(_LATEST_SQL)
        for db_row in result:
            try:
                snap: dict[str, Any] = json.loads(db_row.snapshot_json)
            except Exception:
                continue

            repo = snap.get("repo") or {}
            team = repo.get("team") or ""
            status_ryg = snap.get("status_ryg") or ""

            if status_filter and status_filter != "all" and status_ryg != status_filter:
                continue
            if team_filter and team != team_filter:
                continue

            last_commit = snap.get("last_commit_at") or ""
            docs_missing = snap.get("docs_missing") or []

            rows.append({
                "owner":            db_row.owner,
                "name":             db_row.name,
                "team":             team,
                "dev_owner":        repo.get("dev_owner_name") or "",
                "status_ryg":       status_ryg,
                "status_exp":       snap.get("status_explanation") or "",
                "commits_7d":       snap.get("commits_7d") if snap.get("commits_7d") is not None else "",
                "last_commit":      last_commit,
                "days_since":       _days_since(last_commit),
                "ci_status":        snap.get("ci_status") or "",
                "docs_missing_count": len(docs_missing) if isinstance(docs_missing, list) else 0,
                "tests_present":    snap.get("tests_present"),
                "captured_at":      str(db_row.captured_at),
            })

    rows.sort(key=lambda r: (_RYG_ORDER.get(r["status_ryg"], 9), r["owner"], r["name"]))
    return rows


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

_CSS = """
body { font-family: system-ui, sans-serif; margin: 0; padding: 16px; background: #f4f6f8; color: #222; }
h1 { margin-bottom: 4px; font-size: 1.4em; }
.counters { display: flex; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.counter { padding: 6px 14px; border-radius: 4px; font-size: 0.9em; font-weight: bold; color: #fff; }
.counter.red    { background: #c0392b; }
.counter.yellow { background: #f39c12; color: #000; }
.counter.green  { background: #27ae60; }
.counter.total  { background: #2c3e50; }
.filters { margin-bottom: 12px; font-size: 0.9em; }
.filters label { margin-right: 6px; }
.filters select { margin-right: 16px; }
table { border-collapse: collapse; width: 100%; background: #fff; border-radius: 6px; overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,.1); }
th { background: #2c3e50; color: #fff; padding: 8px 12px; text-align: left; font-size: 0.85em; }
td { padding: 7px 12px; border-bottom: 1px solid #eee; font-size: 0.85em; vertical-align: top; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f0f4f8; }
.exp { color: #555; max-width: 320px; }
.none { color: #aaa; }
a { color: #2980b9; text-decoration: none; }
a:hover { text-decoration: underline; }
"""

_FILTER_FORM = """
<form method="get" class="filters">
  <label>Status:
    <select name="status" onchange="this.form.submit()">
      <option value="all"{sel_all}>All</option>
      <option value="red"{sel_red}>Red</option>
      <option value="yellow"{sel_yellow}>Yellow</option>
      <option value="green"{sel_green}>Green</option>
    </select>
  </label>
  <label>Team: <input name="team" value="{team_val}" size="16">
    <button type="submit">Filter</button>
  </label>
</form>
"""

_NONE = '<span class="none">—</span>'


def _render_html(rows: list[dict[str, Any]], status_filter: str, team_filter: str) -> str:
    def sel(v: str) -> str:
        return ' selected' if status_filter == v else ''

    filter_html = _FILTER_FORM.format(
        sel_all=sel("all"),
        sel_red=sel("red"),
        sel_yellow=sel("yellow"),
        sel_green=sel("green"),
        team_val=_esc(team_filter),
    )

    # Counters (respecting current filters)
    n_red    = sum(1 for r in rows if r["status_ryg"] == "red")
    n_yellow = sum(1 for r in rows if r["status_ryg"] == "yellow")
    n_green  = sum(1 for r in rows if r["status_ryg"] == "green")
    n_total  = len(rows)

    counters_html = (
        '<div class="counters">'
        f'<span class="counter red">Red: {n_red}</span>'
        f'<span class="counter yellow">Yellow: {n_yellow}</span>'
        f'<span class="counter green">Green: {n_green}</span>'
        f'<span class="counter total">Total shown: {n_total}</span>'
        '</div>'
    )

    header = (
        "<tr>"
        "<th>Repo</th>"
        "<th>Team</th>"
        "<th>Status</th>"
        "<th>Explanation</th>"
        "<th>Commits 7d</th>"
        "<th>Days Since Commit</th>"
        "<th>CI</th>"
        "<th>Docs Missing</th>"
        "<th>Tests</th>"
        "<th>Captured At</th>"
        "</tr>"
    )

    body_rows: list[str] = []
    for r in rows:
        owner_esc = _esc(r["owner"])
        name_esc  = _esc(r["name"])
        repo_link = f'<a href="/repo/{owner_esc}/{name_esc}">{owner_esc}/{name_esc}</a>'

        exp = f'<span class="exp">{_esc(r["status_exp"])}</span>' if r["status_exp"] else _NONE
        commits = _esc(r["commits_7d"]) if r["commits_7d"] != "" else _NONE

        days = r["days_since"]
        days_cell = _esc(days) if days is not None else _NONE

        ci = _esc(r["ci_status"]) if r["ci_status"] else _NONE

        docs_count = r["docs_missing_count"]
        docs_cell = _esc(docs_count) if docs_count > 0 else "0"

        tp = r["tests_present"]
        if tp is True:
            tests_cell = "YES"
        elif tp is False:
            tests_cell = "NO"
        else:
            tests_cell = _NONE

        team_cell = _esc(r["team"]) if r["team"] else _NONE

        body_rows.append(
            f"<tr>"
            f"<td>{repo_link}</td>"
            f"<td>{team_cell}</td>"
            f"<td>{_badge(r['status_ryg'])}</td>"
            f"<td>{exp}</td>"
            f"<td>{commits}</td>"
            f"<td>{days_cell}</td>"
            f"<td>{ci}</td>"
            f"<td>{docs_cell}</td>"
            f"<td>{tests_cell}</td>"
            f"<td>{_esc(r['captured_at'])}</td>"
            f"</tr>"
        )

    table = (
        f"<table><thead>{header}</thead><tbody>{''.join(body_rows)}</tbody></table>"
        if rows else "<p>No snapshots match the current filters.</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>RepoPulse Dashboard</title>
  <style>{_CSS}</style>
</head>
<body>
  <h1>RepoPulse Dashboard</h1>
  {counters_html}
  {filter_html}
  {table}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Risk heatmap helpers
# ---------------------------------------------------------------------------

_SEV_ORDER = {"red": 0, "yellow": 1, "green": 2}


def _flag_category(rf: dict[str, Any]) -> str:
    """Return the display category for a single risk flag dict."""
    label = (rf.get("label") or "").strip()
    if label:
        return label
    rid = rf.get("id") or ""
    return rid.split("_")[0] if rid else "unknown"


def _highest_severity(flags: list[dict[str, Any]], category: str) -> str | None:
    """Return the highest severity (red > yellow > green) for flags matching category, or None."""
    best: str | None = None
    for rf in flags:
        if not isinstance(rf, dict):
            continue
        if _flag_category(rf) != category:
            continue
        sev = (rf.get("severity") or "").lower()
        if sev not in _SEV_ORDER:
            continue
        if best is None or _SEV_ORDER[sev] < _SEV_ORDER[best]:
            best = sev
    return best


def _load_risk_rows(team_filter: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (rows, sorted_categories).

    Each row contains: owner, name, team, flags (list of risk flag dicts).
    categories is the union of all flag categories across all rows, sorted.
    """
    engine = get_engine(Settings().db_url)
    rows: list[dict[str, Any]] = []
    categories: set[str] = set()

    with engine.connect() as conn:
        result = conn.execute(_LATEST_SQL)
        for db_row in result:
            try:
                snap: dict[str, Any] = json.loads(db_row.snapshot_json)
            except Exception:
                continue

            repo = snap.get("repo") or {}
            team = repo.get("team") or ""

            if team_filter and team != team_filter:
                continue

            flags = [rf for rf in (snap.get("risk_flags") or []) if isinstance(rf, dict)]
            for rf in flags:
                categories.add(_flag_category(rf))

            rows.append({
                "owner": db_row.owner,
                "name":  db_row.name,
                "team":  team,
                "flags": flags,
            })

    rows.sort(key=lambda r: (r["owner"], r["name"]))
    return rows, sorted(categories)


def _render_risks_html(
    rows: list[dict[str, Any]],
    categories: list[str],
    team_filter: str,
) -> str:
    filter_html = (
        '<form method="get" class="filters">'
        f'  <label>Team: <input name="team" value="{_esc(team_filter)}" size="16">'
        '    <button type="submit">Filter</button>'
        '  </label>'
        '</form>'
    )

    if not rows:
        body = "<p>No repos match the current filter.</p>"
    else:
        # Header
        fixed_headers = "<th>Repo</th><th>Team</th>"
        cat_headers = "".join(f"<th>{_esc(c)}</th>" for c in categories)
        header = f"<tr>{fixed_headers}{cat_headers}</tr>"

        # Body
        body_rows: list[str] = []
        for r in rows:
            owner_esc = _esc(r["owner"])
            name_esc  = _esc(r["name"])
            repo_link = f'<a href="/">{owner_esc}/{name_esc}</a>'
            team_cell = _esc(r["team"]) if r["team"] else _NONE

            cells = f"<td>{repo_link}</td><td>{team_cell}</td>"
            for cat in categories:
                sev = _highest_severity(r["flags"], cat)
                cells += f"<td>{_badge(sev) if sev else ''}</td>"
            body_rows.append(f"<tr>{cells}</tr>")

        body = f"<table><thead>{header}</thead><tbody>{''.join(body_rows)}</tbody></table>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>RepoPulse — Risk Heatmap</title>
  <style>{_CSS}</style>
</head>
<body>
  <h1>Risk Heatmap</h1>
  <p><a href="/">&larr; Portfolio Overview</a></p>
  {filter_html}
  {body}
</body>
</html>"""


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="RepoPulse Dashboard")


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    status: Optional[str] = "all",
    team: Optional[str] = "",
) -> HTMLResponse:
    status = (status or "all").lower()
    if status not in ("all", "red", "yellow", "green"):
        status = "all"
    team = (team or "").strip()

    rows = _load_rows(status_filter=status, team_filter=team)
    html = _render_html(rows, status_filter=status, team_filter=team)
    return HTMLResponse(content=html)


@app.get("/risks", response_class=HTMLResponse)
async def risks(
    request: Request,
    team: Optional[str] = "",
) -> HTMLResponse:
    team = (team or "").strip()
    rows, categories = _load_risk_rows(team_filter=team)
    html = _render_risks_html(rows, categories, team_filter=team)
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    uvicorn.run(app, host=host, port=port)
