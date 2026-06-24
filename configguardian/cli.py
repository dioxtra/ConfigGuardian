"""Typer command-line interface for ConfigGuardian."""

from pathlib import Path
from time import sleep
from typing import Any, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from configguardian.alerts.manager import AlertManager
from configguardian.core.analyzer import create_default_engine
from configguardian.core.database import Database
from configguardian.core.config_loader import load_alert_manager_from_config
from configguardian.core.diff_engine import DiffEngine
from configguardian.core.monitor import Monitor
from configguardian.core.rollback import RollbackService
from configguardian.core.snapshot import SnapshotService
from configguardian.core.timeline import TimelineService
from configguardian.reports.html_report import HtmlReport
from configguardian.utils.constants import DEFAULT_DATABASE_PATH, DEFAULT_WATCHED_FILES
from configguardian.utils.logger import get_logger

app = typer.Typer(help="Monitor, snapshot, and analyze Linux config files.")
console = Console()
logger = get_logger(__name__)


def _database(db_path: Optional[Path] = None) -> Database:
    """Create a database dependency for CLI commands."""
    return Database(db_path or DEFAULT_DATABASE_PATH)


def _load_watched_files(config_path: Optional[Path]) -> list[Path | str]:
    """Load watched files from a YAML config or return defaults."""
    if config_path is None:
        return list(DEFAULT_WATCHED_FILES)

    try:
        import yaml

        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, ImportError) as exc:
        logger.exception("Failed to load config file %s: %s", config_path, exc)
        return list(DEFAULT_WATCHED_FILES)

    if isinstance(config, dict) and isinstance(config.get("watched_files"), list):
        return [str(path) for path in config["watched_files"]]

    if isinstance(config, list):
        return [str(path) for path in config]

    return list(DEFAULT_WATCHED_FILES)


def _load_yaml_config(config_path: Optional[Path]) -> dict[str, Any]:
    """Load a YAML configuration file into a dictionary."""
    if config_path is None:
        return {}

    try:
        import yaml

        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, ImportError) as exc:
        logger.exception("Failed to load config file %s: %s", config_path, exc)
        return {}

    if isinstance(loaded, dict):
        return loaded

    return {}


@app.command("init")
def init() -> None:
    """Initialize local ConfigGuardian storage."""
    database = _database()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Preparing storage...", total=None)
        database.initialize()
    console.print("[green]ConfigGuardian storage initialized.[/green]")


@app.command("monitor")
def monitor(config_path: Optional[Path] = typer.Option(None, "--config", "-c")) -> None:
    """Start file monitoring."""
    database = _database()
    alert_manager = (
        load_alert_manager_from_config(_load_yaml_config(config_path))
        if config_path is not None
        else AlertManager()
    )
    service = Monitor(
        database=database,
        config_path=config_path,
        analyzer_engine=create_default_engine(),
        alert_manager=alert_manager,
    )
    service.start()
    console.print("[green]ConfigGuardian monitor started. Press Ctrl+C to stop.[/green]")

    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        service.stop()
        console.print("[yellow]ConfigGuardian monitor stopped.[/yellow]")


@app.command("snapshot")
def snapshot(config_path: Optional[Path] = typer.Option(None, "--config", "-c")) -> None:
    """Create a snapshot for watched files."""
    service = SnapshotService(
        database=_database(),
        watched_files=_load_watched_files(config_path),
    )
    snapshot_ids = service.create_all()
    console.print(f"[green]Created {len(snapshot_ids)} snapshot record(s).[/green]")


@app.command("diff")
def diff(
    old_snapshot_id: Optional[int] = typer.Option(None, "--old"),
    new_snapshot_id: Optional[int] = typer.Option(None, "--new"),
) -> None:
    """Compare two snapshots."""
    engine = DiffEngine(database=_database())
    table = Table(title="Snapshot Diff")
    table.add_column("File")
    table.add_column("Summary")
    table.add_column("Added")
    table.add_column("Removed")

    results = engine.compare(old_snapshot_id, new_snapshot_id)
    for change in results:
        table.add_row(
            change.file_path,
            change.summary,
            "\n".join(change.added_lines) or "-",
            "\n".join(change.removed_lines) or "-",
        )

    console.print(table)
    if not results:
        console.print("[yellow]No comparable snapshots found.[/yellow]")


@app.command("rollback")
def rollback(snapshot_id: int) -> None:
    """Restore a file from a snapshot."""
    service = RollbackService(database=_database())
    try:
        backup_path = service.restore(snapshot_id)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    console.print(f"[green]Rollback complete. Backup: {backup_path}[/green]")


@app.command("timeline")
def timeline(limit: int = typer.Option(100, "--limit", "-n")) -> None:
    """Show recorded file events."""
    service = TimelineService(database=_database())
    table = Table(title="Timeline")
    table.add_column("Time")
    table.add_column("File")
    table.add_column("Event")
    table.add_column("Severity")

    events = service.list_events(limit=limit)
    for event in events:
        table.add_row(
            event.created_at.isoformat(sep=" "),
            event.file_path,
            event.event_type,
            event.severity,
        )

    console.print(table)
    if not events:
        console.print("[yellow]No events recorded yet.[/yellow]")


@app.command("report")
def report() -> None:
    """Generate an HTML report."""
    report_path = HtmlReport(database=_database()).generate()
    console.print(f"[green]Report generated: {report_path}[/green]")


@app.command("config")
def config(config_path: Optional[Path] = typer.Option(None, "--config", "-c")) -> None:
    """Show effective configuration."""
    table = Table(title="ConfigGuardian Configuration")
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("Database", str(DEFAULT_DATABASE_PATH))
    table.add_row("Watched files", "\n".join(str(path) for path in _load_watched_files(config_path)))
    console.print(table)


@app.command("status")
def status() -> None:
    """Show ConfigGuardian status."""
    database = _database()
    table = Table(title="ConfigGuardian Status")
    table.add_column("Component")
    table.add_column("State")
    table.add_row("Database", str(database.path))
    table.add_row("Database exists", "yes" if database.path.exists() else "no")
    table.add_row("Default watched files", str(len(DEFAULT_WATCHED_FILES)))
    table.add_row("Monitoring", "stopped")
    console.print(table)
