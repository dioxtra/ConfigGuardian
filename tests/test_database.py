"""Database smoke tests."""

from pathlib import Path

from configguardian.core.database import Database


def test_database_initializes_expected_tables(tmp_path: Path) -> None:
    """Database initialization creates required tables."""
    database = Database(tmp_path / "database.db")
    database.initialize()

    with database.connect() as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    table_names = {row[0] for row in rows}
    assert {"snapshots", "events", "alerts", "timeline"} <= table_names


def test_database_round_trips_events_and_snapshots(tmp_path: Path) -> None:
    """Database stores and retrieves event and snapshot records."""
    database = Database(tmp_path / "database.db")

    event_id = database.insert_event(
        file_path="/tmp/app.conf",
        event_type="modified",
        severity="INFO",
        details="File /tmp/app.conf modified",
        timestamp="2026-06-23T21:10:00+00:00",
    )
    snapshot_id = database.insert_snapshot(
        file_path="/tmp/app.conf",
        file_hash="abc123",
        content="value=2\n",
        size=8,
        timestamp="2026-06-23T21:11:00+00:00",
    )

    events = database.get_events("/tmp/app.conf")
    snapshot = database.get_snapshot(snapshot_id)

    assert event_id == events[0]["id"]
    assert snapshot is not None
    assert snapshot["id"] == snapshot_id
    assert snapshot["content"] == "value=2\n"
