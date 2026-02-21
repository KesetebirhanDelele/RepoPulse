from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import typer

from app.logging_setup import configure_logging
from app.settings import Settings
from app.storage.db import init_db
from app.storage.run_store import RunStore
from app.storage.snapshot_store import SnapshotStore
from app.storage.repo_store import RepoStore

from app.github.github_client import GitHubClient
from app.collector.commits import CommitsCollector
from app.collector.actions import ActionsCollector
from app.collector.releases import ReleasesCollector
from app.collector.readme import ReadmeCollector
from app.collector.tree_scan import TreeScanCollector

from app.scoring.engine import ScoringEngine
from app.reporting.csv_export import export_latest_snapshot_csv
from app.reporting.weekly import export_weekly_csv
from app.reporting.deepdive import export_deepdive_queue_csv

cli = typer.Typer(add_completion=False)
repos_app = typer.Typer()
snapshots_app = typer.Typer()
report_app = typer.Typer()
dashboard_app = typer.Typer()
deepdive_app = typer.Typer()
db_app = typer.Typer()
validate_app = typer.Typer()

cli.add_typer(repos_app, name="repos")
cli.add_typer(snapshots_app, name="snapshots")
cli.add_typer(report_app, name="report")
cli.add_typer(dashboard_app, name="dashboard")
cli.add_typer(deepdive_app, name="deepdive")
cli.add_typer(db_app, name="db")
cli.add_typer(validate_app, name="validate")


@repos_app.command("import")
def repos_import(path: Path = typer.Option(..., "--path")):
    """Import repos from a YAML file into sqlite."""
    configure_logging()
    s = Settings()
    init_db(s.db_path)
    store = RepoStore(s.db_path)
    n = store.import_from_yaml(path)
    typer.echo(f"Imported {n} repos.")


@repos_app.command("add")
def repos_add(
    url: str = typer.Option(..., "--url"),
    owner: str = typer.Option(..., "--owner"),
    dev_name: str = typer.Option(None, "--dev-name"),
    team: str = typer.Option(None, "--team"),
):
    configure_logging()
    s = Settings()
    init_db(s.db_path)
    store = RepoStore(s.db_path)
    store.add_repo(url=url, owner=owner, dev_owner_name=dev_name, team=team)
    typer.echo("Repo added.")


@snapshots_app.command("run")
def snapshots_run(
    repos_path: Path = typer.Option(Path("configs/repos.yaml"), "--repos"),
    config_path: Path = typer.Option(Path("configs/default.yaml"), "--config"),
    signals_path: Path = typer.Option(Path("configs/signals.yaml"), "--signals"),
    out_csv: Path = typer.Option(Path("exports/latest_snapshot.csv"), "--out"),
):
    configure_logging()
    s = Settings()
    init_db(s.db_path)

    run_store = RunStore(s.db_path)
    repo_store = RepoStore(s.db_path)
    snapshot_store = SnapshotStore(s.db_path)

    run_id = run_store.start_run(
        repos_path=repos_path,
        config_path=config_path,
        signals_path=signals_path,
        db_path=s.db_path,
        api_mode="token" if s.github_token else "no-token",
    )

    gh = GitHubClient(token=s.github_token)
    scoring = ScoringEngine.from_paths(config_path=config_path)

    # Load repos into DB each time for MVP simplicity
    repo_store.import_from_yaml(repos_path)
    repos = repo_store.list_repos()

    # Collectors (enable/disable based on signals config inside each collector)
    collectors = [
        CommitsCollector(gh),
        ActionsCollector(gh),
        ReleasesCollector(gh),
        ReadmeCollector(gh),
        TreeScanCollector(gh),
    ]

    failures: list[dict[str, str]] = []
    snapshots = []

    captured_at = datetime.now(timezone.utc)

    for r in repos:
        try:
            signals: dict = {"repo": r, "captured_at": captured_at, "run_id": run_id}
            for c in collectors:
                signals = c.enrich(signals, signals_path=signals_path)

            snap = scoring.score(signals)
            snapshot_store.upsert_snapshot(snap)
            snapshots.append(snap)
        except Exception as e:
            failures.append({"repo": f"{r['owner']}/{r['name']}", "error": str(e)})

    export_latest_snapshot_csv(snapshots, out_csv)
    run_store.finish_run(run_id, failures=failures, outputs={"latest_csv": str(out_csv)})

    # ── End-of-run summary ──────────────────────────────────────────────────
    total = len(repos)
    n_ok = len(snapshots)
    n_fail = len(failures)

    typer.echo(f"\nRun {run_id} complete.")
    typer.echo(f"  Repos processed : {total}")
    typer.echo(f"  Snapshots written: {n_ok}")
    typer.echo(f"  Failures         : {n_fail}")

    if n_fail > 0:
        # Categorise by failure["type"] → exc class name → "unknown"
        from collections import Counter

        def _category(f: dict) -> str:
            if f.get("type"):
                return f["type"]
            err = f.get("error") or ""
            # "ExcClassName: message" — extract class name if present
            if ":" in err:
                return err.split(":")[0].strip() or "unknown"
            return "unknown"

        cats = Counter(_category(f) for f in failures)
        typer.echo("\n  Failure categories:")
        for cat, count in cats.most_common():
            typer.echo(f"    {cat}: {count}")

        typer.echo(f"\n  Failed repos (up to 10):")
        for f in failures[:10]:
            repo_id = f.get("repo") or "unknown"
            msg = (f.get("error") or "no message")
            # Truncate long messages for readability
            if len(msg) > 120:
                msg = msg[:117] + "..."
            typer.echo(f"    {repo_id}: {msg}")


@report_app.command("weekly")
def report_weekly(
    since: str = typer.Option(..., "--since", help="YYYY-MM-DD"),
    out: Path = typer.Option(Path("exports/weekly.csv"), "--out"),
):
    configure_logging()
    s = Settings()
    init_db(s.db_path)
    export_weekly_csv(db_path=s.db_path, since_date=since, out_path=out)
    typer.echo(f"Wrote {out}.")


@deepdive_app.command("queue")
def deepdive_queue(
    out: Path = typer.Option(Path("exports/deepdive_queue.csv"), "--out"),
):
    configure_logging()
    s = Settings()
    init_db(s.db_path)
    export_deepdive_queue_csv(db_path=s.db_path, out_path=out)
    typer.echo(f"Wrote {out}.")


@dashboard_app.command("run")
def dashboard_run(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
):
    from app.dashboard.server import run_server
    run_server(host=host, port=port)


@db_app.command("check")
def db_check():
    """Connect to the configured database and print table counts."""
    from app.storage.db_check import run_db_check
    s = Settings()
    run_db_check(s.db_url)


@validate_app.command("configs")
def validate_configs(
    repos: Path = typer.Option(Path("configs/repos.yaml"), "--repos"),
    signals: Path = typer.Option(Path("configs/signals.yaml"), "--signals"),
    config: Path = typer.Option(Path("configs/default.yaml"), "--config"),
):
    """Validate repos.yaml, signals.yaml, and default.yaml."""
    from app.validate_configs import validate_all

    results = validate_all(repos_path=repos, signals_path=signals, default_path=config)
    has_error = False
    for r in results:
        typer.echo(str(r))
        if r.level == "ERROR":
            has_error = True
    if has_error:
        raise typer.Exit(code=1)


def main():
    cli()


if __name__ == "__main__":
    main()