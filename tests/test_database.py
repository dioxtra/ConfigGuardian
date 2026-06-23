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


def test_database_writes_to_legacy_schema(tmp_path: Path) -> None:
    """Database remains usable when old skeleton columns still exist."""
    database = Database(tmp_path / "legacy.db")
    with database.connection() as connection:
        connection.executescript(
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_at TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
    database = Database(tmp_path / "legacy.db")

    event_id = database.insert_event(
        "/tmp/app.conf",
        "modified",
        "INFO",
        "File /tmp/app.conf modified",
        "2026-06-23T21:10:00+00:00",
    )
    snapshot_id = database.insert_snapshot(
        "/tmp/app.conf",
        "abc123",
        "value=2\n",
        8,
        "2026-06-23T21:11:00+00:00",
    )

    assert event_id == 1
    assert snapshot_id == 1
    assert database.get_events("/tmp/app.conf")[0]["details"] == "File /tmp/app.conf modified"
    assert database.get_snapshot(snapshot_id)["hash"] == "abc123"
