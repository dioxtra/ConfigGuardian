"""Core service tests."""

from pathlib import Path

import pytest

from configguardian.core.database import Database
from configguardian.core.diff_engine import DiffEngine
from configguardian.core.rollback import RollbackService
from configguardian.core.snapshot import SnapshotService
from configguardian.core.timeline import TimelineService


def test_snapshot_service_persists_existing_files_and_skips_missing(
    tmp_path: Path,
) -> None:
    """Snapshot service persists readable files and ignores missing paths."""
    config_file = tmp_path / "app.conf"
    missing_file = tmp_path / "missing.conf"
    config_file.write_text("enabled=true\n", encoding="utf-8")
    database = Database(tmp_path / "database.db")

    service = SnapshotService(
        database=database,
        watched_files=[config_file, missing_file],
    )
    snapshot_ids = service.create_all()

    assert len(snapshot_ids) == 1
    snapshot = database.get_snapshot(snapshot_ids[0])
    assert snapshot is not None
    assert snapshot["file_path"] == str(config_file)
    assert snapshot["content"] == "enabled=true\n"


def test_diff_engine_compares_two_snapshots(tmp_path: Path) -> None:
    """Diff engine reports added and removed lines."""
    database = Database(tmp_path / "database.db")
    old_id = database.insert_snapshot(
        str(tmp_path / "app.conf"),
        "old",
        "a\nb\n",
        4,
        "2026-06-23T21:10:00+00:00",
    )
    new_id = database.insert_snapshot(
        str(tmp_path / "app.conf"),
        "new",
        "a\nc\n",
        4,
        "2026-06-23T21:11:00+00:00",
    )

    results = DiffEngine(database).compare(old_id, new_id)

    assert len(results) == 1
    assert "c" in results[0].added_lines
    assert "b" in results[0].removed_lines


def test_timeline_service_maps_database_events(tmp_path: Path) -> None:
    """Timeline service returns pydantic event models from database rows."""
    database = Database(tmp_path / "database.db")
    database.insert_event(
        "/tmp/app.conf",
        "modified",
        "INFO",
        "File /tmp/app.conf modified",
        "2026-06-23T21:10:00+00:00",
    )

    events = TimelineService(database).list_events()

    assert len(events) == 1
    assert events[0].file_path == "/tmp/app.conf"
    assert events[0].reason == "File /tmp/app.conf modified"


def test_rollback_service_restores_snapshot_and_creates_backup(tmp_path: Path) -> None:
    """Rollback restores stored content and creates a pre-rollback backup."""
    target = tmp_path / "app.conf"
    target.write_text("current\n", encoding="utf-8")
    database = Database(tmp_path / "database.db")
    snapshot_id = database.insert_snapshot(
        str(target),
        "hash",
        "previous\n",
        9,
        "2026-06-23T21:10:00+00:00",
    )

    backup_path = RollbackService(database).restore(snapshot_id)

    assert target.read_text(encoding="utf-8") == "previous\n"
    assert backup_path.exists()
    assert backup_path.read_text(encoding="utf-8") == "current\n"


def test_rollback_service_rejects_unknown_snapshot(tmp_path: Path) -> None:
    """Rollback raises a clear error for missing snapshots."""
    database = Database(tmp_path / "database.db")

    with pytest.raises(ValueError, match="Snapshot not found"):
        RollbackService(database).restore(999)
