"""Minimal server-rendered HTML dashboard backed by SQL Server snapshots."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote_plus

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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

_LATEST_ONE_SQL = text("""
    SELECT s.owner, s.name, s.captured_at, s.snapshot_json
    FROM snapshots s
    INNER JOIN (
        SELECT owner, name, MAX(captured_at) AS max_cap
        FROM snapshots
        WHERE owner = :owner AND name = :name
        GROUP BY owner, name
    ) latest
        ON  s.owner       = latest.owner
        AND s.name        = latest.name
        AND s.captured_at = latest.max_cap
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


def _format_risk_flags(raw: Any) -> str:
    """Return a human-readable semicolon-joined string of risk flag ids."""
    if isinstance(raw, list):
        parts = [rf.get("id") or rf.get("label") or "" for rf in raw if isinstance(rf, dict)]
        return ";".join(p for p in parts if p)
    if isinstance(raw, str):
        return raw
    return ""


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
                "risk_flags_raw":   snap.get("risk_flags"),
                "latest_tag":       snap.get("latest_tag") or "",
                "latest_release":   snap.get("latest_release") or "",
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
.nav-bar { font-size: 0.85em; margin-bottom: 12px; }
.nav-bar a { margin-right: 14px; }
.msg-box { padding: 10px 14px; border-radius: 4px; margin-bottom: 14px; font-size: 0.9em; }
.msg-box.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.msg-box.info    { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
.invalid-list { list-style: none; padding: 0; margin: 6px 0 0; }
.invalid-list li { color: #c0392b; font-size: 0.85em; }
form.manage-form { background: #fff; padding: 16px; border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0,0,0,.1); margin-bottom: 16px; max-width: 680px; }
form.manage-form label { display: block; margin-bottom: 6px; font-size: 0.9em; font-weight: 500; }
form.manage-form textarea,
form.manage-form input[type=text] { width: 100%; box-sizing: border-box; padding: 6px 8px;
  border: 1px solid #ccc; border-radius: 3px; font-family: monospace; font-size: 0.85em; }
form.manage-form textarea { height: 120px; resize: vertical; }
.btn { display: inline-block; padding: 7px 16px; border-radius: 4px; border: none;
  cursor: pointer; font-size: 0.9em; font-weight: bold; }
.btn-primary { background: #2980b9; color: #fff; }
.btn-primary:hover { background: #2471a3; }
.btn-success { background: #27ae60; color: #fff; }
.btn-success:hover { background: #1e8449; }
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


def _render_html(rows: list[dict[str, Any]], status_filter: str, team_filter: str, message: str = "") -> str:
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

    # Captured At: max across shown rows
    max_cap = max((r["captured_at"] for r in rows), default="") if rows else ""
    cap_line = (
        f'<p style="font-size:0.85em;color:#555;margin:0 0 10px">Captured At: {_esc(max_cap)}</p>'
        if max_cap else ""
    )

    header = (
        "<tr>"
        "<th>Project</th>"
        "<th>Developer</th>"
        "<th>Commits 7d</th>"
        "<th>Status</th>"
        "<th>Explanation</th>"
        "<th>Risk Flags</th>"
        "<th>Latest Tag</th>"
        "<th>Latest Release</th>"
        "</tr>"
    )

    body_rows: list[str] = []
    for r in rows:
        owner_esc = _esc(r["owner"])
        name_esc  = _esc(r["name"])
        repo_link = (
            f'<a href="/audit?owner={owner_esc}&amp;name={name_esc}">'
            f'{owner_esc}/{name_esc}</a>'
        )

        dev_cell = _esc(r["dev_owner"]) if r["dev_owner"] else _NONE
        commits  = _esc(r["commits_7d"]) if r["commits_7d"] != "" else _NONE
        exp      = f'<span class="exp">{_esc(r["status_exp"])}</span>' if r["status_exp"] else _NONE

        rf_str  = _format_risk_flags(r["risk_flags_raw"])
        rf_cell = _esc(rf_str) if rf_str else _NONE

        body_rows.append(
            f"<tr>"
            f"<td>{repo_link}</td>"
            f"<td>{dev_cell}</td>"
            f"<td>{commits}</td>"
            f"<td>{_badge(r['status_ryg'])}</td>"
            f"<td>{exp}</td>"
            f"<td>{rf_cell}</td>"
            f"<td>{_esc(r['latest_tag']) if r['latest_tag'] else _NONE}</td>"
            f"<td>{_esc(r['latest_release']) if r['latest_release'] else _NONE}</td>"
            f"</tr>"
        )

    table = (
        f"<table><thead>{header}</thead><tbody>{''.join(body_rows)}</tbody></table>"
        if rows else "<p>No snapshots match the current filters.</p>"
    )

    msg_html = (
        f'<div class="msg-box info">{_esc(message)}</div>'
        if message else ""
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
  <div class="nav-bar">
    <a href="/manage">&#9881; Manage Repos</a>
    <a href="/risks">Risk Heatmap</a>
    <a href="/support">Ownership &amp; Support</a>
  </div>
  {msg_html}
  {counters_html}
  {cap_line}
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
# Developer audit helpers
# ---------------------------------------------------------------------------

_AUDIT_DOCS_DEFAULTS = [
    "docs/architecture.md",
    "docs/data-model.md",
    "docs/operations.md",
]


def _load_audit_row(owner: str, name: str) -> dict[str, Any] | None:
    engine = get_engine(Settings().db_url)
    with engine.connect() as conn:
        result = conn.execute(_LATEST_ONE_SQL, {"owner": owner, "name": name})
        db_row = result.fetchone()
        if db_row is None:
            return None
        try:
            snap: dict[str, Any] = json.loads(db_row.snapshot_json)
        except Exception:
            return None

    repo = snap.get("repo") or {}
    docs_missing = snap.get("docs_missing")
    if not isinstance(docs_missing, list):
        docs_missing = _AUDIT_DOCS_DEFAULTS

    return {
        "owner":             db_row.owner,
        "name":              db_row.name,
        "dev_owner":         repo.get("dev_owner_name") or "",
        "captured_at":       str(db_row.captured_at),
        "readme_present":    snap.get("readme_present", False),
        "tests_present":     snap.get("tests_present", False),
        "docs_missing":      docs_missing,
        "gitignore_present":  snap.get("gitignore_present", False),
        "env_not_tracked":    snap.get("env_not_tracked", True),
        "claude_md_present":  snap.get("claude_md_present", False),
    }


def _render_audit_html(row: dict[str, Any]) -> str:
    owner_esc = _esc(row["owner"])
    name_esc  = _esc(row["name"])
    dev_esc   = _esc(row["dev_owner"]) if row["dev_owner"] else "—"
    cap_esc   = _esc(row["captured_at"])

    def _bool_cell(val: Any) -> str:
        return "✅" if val else "❌"

    docs_missing: list[str] = row["docs_missing"]
    if not docs_missing:
        docs_cell = "✅"
    else:
        joined = _esc(";".join(docs_missing))
        docs_cell = f'❌ <span style="font-size:0.8em;color:#555">{joined}</span>'

    audit_header = (
        "<tr>"
        "<th>README</th><th>Tests</th><th>Docs Missing</th>"
        "<th>.gitignore</th><th>CLAUDE.md</th><th>Env Not Tracked</th>"
        "</tr>"
    )
    audit_row = (
        "<tr>"
        f"<td>{_bool_cell(row['readme_present'])}</td>"
        f"<td>{_bool_cell(row['tests_present'])}</td>"
        f"<td>{docs_cell}</td>"
        f"<td>{_bool_cell(row['gitignore_present'])}</td>"
        f"<td>{_bool_cell(row['claude_md_present'])}</td>"
        f"<td>{_bool_cell(row['env_not_tracked'])}</td>"
        "</tr>"
    )
    table = f"<table><thead>{audit_header}</thead><tbody>{audit_row}</tbody></table>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>RepoPulse &mdash; Audit: {owner_esc}/{name_esc}</title>
  <style>{_CSS}</style>
</head>
<body>
  <h1>Developer Audit</h1>
  <p><a href="/">&larr; Portfolio Overview</a></p>
  <p style="font-size:0.9em">Developer: <strong>{dev_esc}</strong> &nbsp;|&nbsp; Project: <strong>{owner_esc}/{name_esc}</strong> &nbsp;|&nbsp; Captured At: {cap_esc}</p>
  <h2 style="font-size:1.1em;margin-top:16px">File Audit</h2>
  {table}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Ownership & Support helpers
# ---------------------------------------------------------------------------

def _compute_support_flags(snap: dict[str, Any], stale_days: int) -> list[str]:
    """Return active support flag names for a snapshot."""
    flags: list[str] = []

    docs_missing = snap.get("docs_missing")
    if isinstance(docs_missing, list) and len(docs_missing) > 0:
        flags.append("missing_docs")

    if snap.get("tests_present") is False:
        flags.append("no_tests")

    if snap.get("ci_status") == "failure":
        flags.append("ci_failing")

    last_commit = snap.get("last_commit_at") or ""
    days = _days_since(last_commit)
    if days is not None:
        if days >= stale_days:
            flags.append("stale")
    else:
        if snap.get("commits_7d") == 0:
            flags.append("stale")

    if snap.get("env_not_tracked") is False:
        flags.append("env_tracked")

    if snap.get("gitignore_present") is False:
        flags.append("missing_gitignore")

    return flags


def _load_support_rows(team_filter: str, stale_days: int) -> list[dict[str, Any]]:
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

            if team_filter and team != team_filter:
                continue

            flags = _compute_support_flags(snap, stale_days)
            last_commit = snap.get("last_commit_at") or ""
            docs_missing = snap.get("docs_missing") or []

            rows.append({
                "owner":              db_row.owner,
                "name":               db_row.name,
                "team":               team or "Unassigned",
                "dev_owner":          repo.get("dev_owner_name") or "Unassigned",
                "status_ryg":         snap.get("status_ryg") or "",
                "days_since":         _days_since(last_commit),
                "ci_status":          snap.get("ci_status") or "",
                "docs_missing_count": len(docs_missing) if isinstance(docs_missing, list) else 0,
                "tests_present":      snap.get("tests_present"),
                "support_flags":      flags,
                "support_flags_str":  ";".join(flags),
                "captured_at":        str(db_row.captured_at),
            })

    return rows


def _render_support_html(
    rows: list[dict[str, Any]],
    team_filter: str,
    stale_days: int,
) -> str:
    filter_html = (
        '<form method="get" class="filters">'
        f'  <label>Team: <input name="team" value="{_esc(team_filter)}" size="16"></label>'
        f'  <label>Stale days: <input name="stale_days" type="number" value="{stale_days}" size="4" min="1"></label>'
        '  <button type="submit">Filter</button>'
        '</form>'
    )

    # ---- Rollup by (team, dev_owner) ----
    GroupKey = tuple[str, str]
    groups: dict[GroupKey, dict[str, Any]] = {}

    for r in rows:
        key: GroupKey = (r["team"], r["dev_owner"])
        if key not in groups:
            groups[key] = {
                "team": r["team"], "dev_owner": r["dev_owner"],
                "apps_total": 0, "reds_count": 0, "yellows_count": 0,
                "missing_docs_count": 0, "no_tests_count": 0,
                "ci_failing_count": 0, "stale_count": 0,
                "env_tracked_count": 0, "missing_gitignore_count": 0,
            }
        g = groups[key]
        g["apps_total"] += 1
        if r["status_ryg"] == "red":
            g["reds_count"] += 1
        if r["status_ryg"] == "yellow":
            g["yellows_count"] += 1
        sf = r["support_flags"]
        if "missing_docs"     in sf: g["missing_docs_count"] += 1
        if "no_tests"         in sf: g["no_tests_count"] += 1
        if "ci_failing"       in sf: g["ci_failing_count"] += 1
        if "stale"            in sf: g["stale_count"] += 1
        if "env_tracked"      in sf: g["env_tracked_count"] += 1
        if "missing_gitignore" in sf: g["missing_gitignore_count"] += 1

    sorted_groups = sorted(groups.values(), key=lambda g: (g["team"], g["dev_owner"]))

    rollup_header = (
        "<tr>"
        "<th>Team</th><th>Dev Owner</th><th>Apps</th>"
        "<th>Red</th><th>Yellow</th>"
        "<th>Missing Docs</th><th>No Tests</th><th>CI Failing</th>"
        "<th>Stale</th><th>Env Tracked</th><th>Missing .gitignore</th>"
        "</tr>"
    )
    rollup_rows: list[str] = []
    for g in sorted_groups:
        rollup_rows.append(
            "<tr>"
            f"<td>{_esc(g['team'])}</td>"
            f"<td>{_esc(g['dev_owner'])}</td>"
            f"<td>{g['apps_total']}</td>"
            f"<td>{g['reds_count'] or ''}</td>"
            f"<td>{g['yellows_count'] or ''}</td>"
            f"<td>{g['missing_docs_count'] or ''}</td>"
            f"<td>{g['no_tests_count'] or ''}</td>"
            f"<td>{g['ci_failing_count'] or ''}</td>"
            f"<td>{g['stale_count'] or ''}</td>"
            f"<td>{g['env_tracked_count'] or ''}</td>"
            f"<td>{g['missing_gitignore_count'] or ''}</td>"
            "</tr>"
        )

    rollup_table = (
        f"<table><thead>{rollup_header}</thead><tbody>{''.join(rollup_rows)}</tbody></table>"
        if sorted_groups else "<p>No data.</p>"
    )

    # ---- Apps needing attention ----
    attention = [
        r for r in rows
        if r["status_ryg"] in ("red", "yellow") or r["support_flags"]
    ]
    attention.sort(key=lambda r: (
        _RYG_ORDER.get(r["status_ryg"], 9), r["team"], r["dev_owner"], r["owner"], r["name"]
    ))

    attn_header = (
        "<tr>"
        "<th>Repo</th><th>Team</th><th>Dev Owner</th><th>Status</th>"
        "<th>Days Since Commit</th><th>CI</th><th>Docs Missing</th>"
        "<th>Tests</th><th>Support Flags</th><th>Captured At</th>"
        "</tr>"
    )
    attn_rows: list[str] = []
    for r in attention:
        owner_esc = _esc(r["owner"])
        name_esc  = _esc(r["name"])
        repo_link = f'<a href="/repo/{owner_esc}/{name_esc}">{owner_esc}/{name_esc}</a>'

        days = r["days_since"]
        days_cell = _esc(days) if days is not None else _NONE
        ci = _esc(r["ci_status"]) if r["ci_status"] else _NONE

        tp = r["tests_present"]
        if tp is True:
            tests_cell = "YES"
        elif tp is False:
            tests_cell = "NO"
        else:
            tests_cell = _NONE

        sf = _esc(r["support_flags_str"]) if r["support_flags_str"] else _NONE

        attn_rows.append(
            "<tr>"
            f"<td>{repo_link}</td>"
            f"<td>{_esc(r['team'])}</td>"
            f"<td>{_esc(r['dev_owner'])}</td>"
            f"<td>{_badge(r['status_ryg'])}</td>"
            f"<td>{days_cell}</td>"
            f"<td>{ci}</td>"
            f"<td>{_esc(r['docs_missing_count'])}</td>"
            f"<td>{tests_cell}</td>"
            f"<td>{sf}</td>"
            f"<td>{_esc(r['captured_at'])}</td>"
            "</tr>"
        )

    attn_table = (
        f"<table><thead>{attn_header}</thead><tbody>{''.join(attn_rows)}</tbody></table>"
        if attn_rows else "<p>No repos need attention under the current filters.</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>RepoPulse &mdash; Ownership &amp; Support</title>
  <style>{_CSS}</style>
</head>
<body>
  <h1>Ownership &amp; Support</h1>
  <p><a href="/">&larr; Portfolio Overview</a></p>
  {filter_html}
  <h2 style="font-size:1.1em;margin-top:16px">Team / Dev Owner Rollup</h2>
  {rollup_table}
  <h2 style="font-size:1.1em;margin-top:24px">Apps Needing Attention</h2>
  {attn_table}
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
    msg: Optional[str] = "",
) -> HTMLResponse:
    status = (status or "all").lower()
    if status not in ("all", "red", "yellow", "green"):
        status = "all"
    team = (team or "").strip()
    message = (msg or "").strip()

    rows = _load_rows(status_filter=status, team_filter=team)
    html = _render_html(rows, status_filter=status, team_filter=team, message=message)
    return HTMLResponse(content=html)


@app.get("/audit", response_class=HTMLResponse)
async def audit(
    request: Request,
    owner: Optional[str] = "",
    name: Optional[str] = "",
) -> HTMLResponse:
    owner = (owner or "").strip()
    name  = (name or "").strip()
    if not owner or not name:
        return HTMLResponse(content="<p>Missing owner or name parameter.</p>", status_code=400)
    row = _load_audit_row(owner=owner, name=name)
    if row is None:
        return HTMLResponse(
            content=f"<p>No snapshot found for {_esc(owner)}/{_esc(name)}.</p>",
            status_code=404,
        )
    html = _render_audit_html(row)
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


@app.get("/support", response_class=HTMLResponse)
async def support(
    request: Request,
    team: Optional[str] = "",
    stale_days: Optional[int] = 7,
) -> HTMLResponse:
    team = (team or "").strip()
    stale_days = max(1, stale_days or 7)
    rows = _load_support_rows(team_filter=team, stale_days=stale_days)
    html = _render_support_html(rows, team_filter=team, stale_days=stale_days)
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Manage page — helpers
# ---------------------------------------------------------------------------

_GITHUB_PREFIX = "https://github.com/"
_SEGMENT_RE = re.compile(r'^[A-Za-z0-9_.\-]+$')


def _parse_github_url(raw: str) -> tuple[str, str]:
    """Return (owner, name) parsed from a GitHub HTTPS URL.

    Accepts trailing '/' and '.git' suffix.
    Raises ValueError with a human-readable reason on failure.
    """
    url = raw.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    if not url.startswith(_GITHUB_PREFIX):
        raise ValueError("must start with https://github.com/")
    tail = url[len(_GITHUB_PREFIX):]
    parts = [p for p in tail.split("/") if p]
    if len(parts) < 2:
        raise ValueError("cannot parse owner/name — expected https://github.com/owner/name")
    owner, name = parts[0], parts[1]
    if not _SEGMENT_RE.match(owner):
        raise ValueError(f"invalid owner segment: {owner!r}")
    if not _SEGMENT_RE.match(name):
        raise ValueError(f"invalid repo name segment: {name!r}")
    return owner, name


def _upsert_repo(engine: Any, url: str, owner: str, name: str, team: str) -> str:
    """Insert or update a repo row keyed on (owner, name).

    Returns 'added' if a new row was created, 'updated' if an existing row
    was modified.  Team is only overwritten when a non-empty team is supplied.
    """
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id, team FROM repos WHERE owner = :owner AND name = :name"),
            {"owner": owner, "name": name},
        ).fetchone()

        if existing is None:
            conn.execute(
                text(
                    "INSERT INTO repos (url, owner, name, dev_owner_name, team) "
                    "VALUES (:url, :owner, :name, NULL, :team)"
                ),
                {"url": url, "owner": owner, "name": name, "team": team or None},
            )
            return "added"

        # Row exists — update url; only overwrite team when caller supplied one
        new_team = team if team else (existing.team or None)
        conn.execute(
            text(
                "UPDATE repos SET url = :url, team = :team "
                "WHERE owner = :owner AND name = :name"
            ),
            {"url": url, "owner": owner, "name": name, "team": new_team},
        )
        return "updated"


def _run_snapshots_pipeline() -> dict[str, Any]:
    """Run the collect → score → persist pipeline in-process.

    Uses the DB as the authoritative repo list (does NOT reload from YAML),
    so repos registered via the web UI are included.

    Returns a summary dict with keys: processed, written, failures, timestamp.
    """
    # Lazy imports to keep module loading fast and avoid circular dependencies
    from app.storage.db import init_db  # type: ignore
    from app.storage.run_store import RunStore  # type: ignore
    from app.storage.repo_store import RepoStore  # type: ignore
    from app.storage.snapshot_store import SnapshotStore  # type: ignore
    from app.github.github_client import GitHubClient  # type: ignore
    from app.collector.commits import CommitsCollector  # type: ignore
    from app.collector.actions import ActionsCollector  # type: ignore
    from app.collector.releases import ReleasesCollector  # type: ignore
    from app.collector.readme import ReadmeCollector  # type: ignore
    from app.collector.tree_scan import TreeScanCollector  # type: ignore
    from app.scoring.engine import ScoringEngine  # type: ignore
    from app.reporting.csv_export import export_latest_snapshot_csv  # type: ignore

    config_path  = Path("configs/default.yaml")
    signals_path = Path("configs/signals.yaml")
    out_csv      = Path("exports/latest_snapshot.csv")

    s = Settings()
    init_db(s.db_path)

    run_store      = RunStore(s.db_path)
    repo_store     = RepoStore(s.db_path)
    snapshot_store = SnapshotStore(s.db_path)

    run_id = run_store.start_run(
        repos_path=Path("configs/repos.yaml"),  # informational only
        config_path=config_path,
        signals_path=signals_path,
        db_path=s.db_path,
        api_mode="token" if s.github_token else "no-token",
    )

    gh      = GitHubClient(token=s.github_token)
    scoring = ScoringEngine.from_paths(config_path=config_path)

    # DB is the source of truth — do NOT call import_from_yaml here
    repos = repo_store.list_repos()

    collectors = [
        CommitsCollector(gh),
        ActionsCollector(gh),
        ReleasesCollector(gh),
        ReadmeCollector(gh),
        TreeScanCollector(gh),
    ]

    failures:  list[dict[str, str]] = []
    snapshots: list[Any]            = []
    captured_at = datetime.now(timezone.utc)

    for r in repos:
        try:
            signals: dict[str, Any] = {
                "repo": r,
                "captured_at": captured_at,
                "run_id": run_id,
            }
            for c in collectors:
                signals = c.enrich(signals, signals_path=signals_path)
            snap = scoring.score(signals)
            snapshot_store.upsert_snapshot(snap)
            snapshots.append(snap)
        except Exception as exc:
            failures.append({"repo": f"{r['owner']}/{r['name']}", "error": str(exc)})

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    export_latest_snapshot_csv(snapshots, out_csv)
    run_store.finish_run(run_id, failures=failures, outputs={"latest_csv": str(out_csv)})

    return {
        "processed": len(repos),
        "written":   len(snapshots),
        "failures":  len(failures),
        "timestamp": captured_at.isoformat(),
    }


def _load_manage_repos() -> list[dict[str, Any]]:
    """Return all repos from the DB, ordered by owner/name."""
    engine = get_engine(Settings().db_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT owner, name, url, dev_owner_name, team "
                "FROM repos ORDER BY owner, name"
            )
        ).mappings().all()
    return [dict(r) for r in rows]


def _render_manage_html(
    repos: list[dict[str, Any]],
    status: dict[str, Any] | None = None,
) -> str:
    """Render the /manage page with registration form, snapshot button, and repo table."""

    # ---- status message area ------------------------------------------------
    msg_html = ""
    if status:
        action = status.get("action", "")
        if action == "register":
            n_added   = status.get("added", 0)
            n_updated = status.get("updated", 0)
            n_invalid = status.get("invalid", 0)
            summary = (
                f"<strong>Added:</strong> {n_added} &nbsp; "
                f"<strong>Updated:</strong> {n_updated} &nbsp; "
                f"<strong>Skipped/Invalid:</strong> {n_invalid}"
            )
            invalid_items: list[dict[str, str]] = status.get("invalid_items", [])
            inv_html = ""
            if invalid_items:
                items = "".join(
                    f'<li>{_esc(item["line"])} &mdash; {_esc(item["reason"])}</li>'
                    for item in invalid_items
                )
                inv_html = f'<ul class="invalid-list">{items}</ul>'
            msg_html = f'<div class="msg-box success">{summary}{inv_html}</div>'

    # ---- repo table ---------------------------------------------------------
    if repos:
        header = (
            "<tr>"
            "<th>Owner</th><th>Repo</th><th>Team</th>"
            "<th>Developer</th><th>URL</th>"
            "</tr>"
        )
        body_rows: list[str] = []
        for r in repos:
            team_cell = _esc(r.get("team") or "") or "Unassigned"
            dev_cell  = _esc(r.get("dev_owner_name") or "") or _NONE
            url_val   = r.get("url") or ""
            url_cell  = (
                f'<a href="{_esc(url_val)}" target="_blank" rel="noopener">'
                f'{_esc(url_val)}</a>'
                if url_val else _NONE
            )
            body_rows.append(
                "<tr>"
                f"<td>{_esc(r.get('owner', ''))}</td>"
                f"<td>{_esc(r.get('name', ''))}</td>"
                f"<td>{team_cell}</td>"
                f"<td>{dev_cell}</td>"
                f"<td>{url_cell}</td>"
                "</tr>"
            )
        table_html = (
            f"<table><thead>{header}</thead>"
            f"<tbody>{''.join(body_rows)}</tbody></table>"
        )
    else:
        table_html = "<p>No repos registered yet.</p>"

    n_repos = len(repos)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>RepoPulse &mdash; Manage Repos</title>
  <style>{_CSS}</style>
</head>
<body>
  <h1>Manage Repos</h1>
  <div class="nav-bar"><a href="/">&larr; Portfolio Overview</a></div>
  {msg_html}
  <form class="manage-form" method="post" action="/manage/register">
    <label for="repo_urls">
      GitHub repo URLs &mdash; one per line &mdash; <code>.git</code> suffix is fine:
    </label>
    <textarea id="repo_urls" name="repo_urls"
      placeholder="https://github.com/owner/repo&#10;https://github.com/owner/repo2.git"></textarea>
    <br><br>
    <label for="team">
      Team <span style="font-weight:normal;color:#777">(optional &mdash; applies to all URLs above)</span>:
    </label>
    <input type="text" id="team" name="team" placeholder="e.g. Core" size="32">
    <br><br>
    <button type="submit" class="btn btn-primary">Register repos</button>
  </form>

  <form method="post" action="/run/snapshots" style="margin-bottom:24px">
    <button type="submit" class="btn btn-success">&#9654; Generate snapshots</button>
    <span style="font-size:0.85em;color:#555;margin-left:10px">
      Runs collection &amp; scoring for all {n_repos} registered repo(s),
      then redirects to the portfolio view.
    </span>
  </form>

  <h2 style="font-size:1.1em;margin-top:8px">Tracked Repos ({n_repos})</h2>
  {table_html}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Manage page — routes
# ---------------------------------------------------------------------------

@app.get("/manage", response_class=HTMLResponse)
async def manage(request: Request) -> HTMLResponse:
    repos = _load_manage_repos()
    return HTMLResponse(content=_render_manage_html(repos))


@app.post("/manage/register", response_class=HTMLResponse)
async def manage_register(
    repo_urls: str = Form(default=""),
    team: str = Form(default=""),
) -> HTMLResponse:
    team = (team or "").strip()

    raw_lines = [ln.strip() for ln in (repo_urls or "").splitlines()]
    raw_lines = [ln for ln in raw_lines if ln]

    engine = get_engine(Settings().db_url)
    n_added   = 0
    n_updated = 0
    invalid_items: list[dict[str, str]] = []

    for line in raw_lines:
        try:
            owner, name = _parse_github_url(line)
        except ValueError as exc:
            invalid_items.append({"line": line, "reason": str(exc)})
            continue

        canonical_url = f"{_GITHUB_PREFIX}{owner}/{name}"
        result = _upsert_repo(engine, canonical_url, owner, name, team)
        if result == "added":
            n_added += 1
        else:
            n_updated += 1

    repos = _load_manage_repos()
    status = {
        "action":        "register",
        "added":         n_added,
        "updated":       n_updated,
        "invalid":       len(invalid_items),
        "invalid_items": invalid_items,
    }
    return HTMLResponse(content=_render_manage_html(repos, status=status))


@app.post("/run/snapshots")
async def run_snapshots_web() -> RedirectResponse:
    try:
        result = _run_snapshots_pipeline()
        msg = (
            f"Snapshots updated: "
            f"processed={result['processed']}, "
            f"written={result['written']}, "
            f"failures={result['failures']}"
        )
    except Exception as exc:
        msg = f"Snapshot run failed: {exc}"

    return RedirectResponse(url=f"/?msg={quote_plus(msg)}", status_code=303)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    uvicorn.run(app, host=host, port=port)
