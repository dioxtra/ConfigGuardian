"""Production-ready SQLite database layer for ConfigGuardian."""

from collections.abc import Iterator
from contextlib import contextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from sqlite3 import Connection, Row
from threading import RLock
from typing import Any, Optional

from configguardian.utils.logger import get_logger


class DatabaseError(RuntimeError):
    """Raised when a database operation fails."""


class Database:
    """SQLite storage layer using one connection per operation."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.logger = get_logger(__name__)
        self._initialized = False
        self._init_lock = RLock()

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        """Open a configured SQLite connection and manage transactions."""
        conn: Optional[Connection] = None

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                self.path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                timeout=30.0,
            )
            conn.row_factory = Row
            self._configure_connection(conn)
            yield conn
            conn.commit()
        except (sqlite3.Error, OSError) as exc:
            if conn is not None:
                with suppress(sqlite3.Error):
                    conn.rollback()
            self.logger.exception("SQLite operation failed: %s", exc)
            raise DatabaseError("SQLite operation failed") from exc
        finally:
            if conn is not None:
                with suppress(sqlite3.Error):
                    conn.close()

    def connect(self) -> Connection:
        """Open a raw SQLite connection for compatibility with existing callers."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                self.path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                timeout=30.0,
            )
            conn.row_factory = Row
            self._configure_connection(conn)
            return conn
        except (sqlite3.Error, OSError) as exc:
            self.logger.exception("SQLite connection failed: %s", exc)
            raise DatabaseError("SQLite connection failed") from exc

    def initialize(self) -> None:
        """Create required tables, indexes, and compatibility columns."""
        if self._initialized:
            return

        with self._init_lock:
            if self._initialized:
                return

            with self.connection() as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        details TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL,
                        hash TEXT NOT NULL,
                        content TEXT NOT NULL,
                        size INTEGER NOT NULL,
                        timestamp TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS timeline (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    );
                    """
                )
                self._ensure_compatibility_columns(conn)
                self._migrate_legacy_values(conn)
                self._create_indexes(conn)

            self._initialized = True

    def insert_event(
        self,
        file_path: str,
        event_type: str,
        severity: str,
        details: str,
        timestamp: Optional[datetime | str] = None,
    ) -> int:
        """Insert an event and return its database id."""
        self.initialize()
        with self.connection() as conn:
            formatted_timestamp = self._format_timestamp(timestamp)
            columns = self._column_names(conn, "events")
            values: dict[str, Any] = {
                "file_path": file_path,
                "event_type": event_type,
                "timestamp": formatted_timestamp,
                "severity": severity.upper(),
                "details": details,
                "reason": details,
                "created_at": formatted_timestamp,
            }
            cursor = self._insert_dynamic(conn, "events", columns, values)
            return self._lastrowid(cursor)

    def insert_snapshot(
        self,
        file_path: str,
        file_hash: str,
        content: str,
        size: int,
        timestamp: Optional[datetime | str] = None,
    ) -> int:
        """Insert a file snapshot and return its database id."""
        self.initialize()
        safe_size = max(0, int(size))
        with self.connection() as conn:
            formatted_timestamp = self._format_timestamp(timestamp)
            columns = self._column_names(conn, "snapshots")
            values: dict[str, Any] = {
                "file_path": file_path,
                "hash": file_hash,
                "sha256": file_hash,
                "content": content,
                "size": safe_size,
                "size_bytes": safe_size,
                "timestamp": formatted_timestamp,
                "modified_at": formatted_timestamp,
                "created_at": formatted_timestamp,
            }
            cursor = self._insert_dynamic(conn, "snapshots", columns, values)
            return self._lastrowid(cursor)

    def insert_alert(
        self,
        file_path: str,
        severity: str,
        reason: str,
        timestamp: Optional[datetime | str] = None,
    ) -> int:
        """Insert an alert and return its database id."""
        self.initialize()
        with self.connection() as conn:
            formatted_timestamp = self._format_timestamp(timestamp)
            columns = self._column_names(conn, "alerts")
            values: dict[str, Any] = {
                "file_path": file_path,
                "severity": severity.upper(),
                "reason": reason,
                "message": reason,
                "provider": "internal",
                "timestamp": formatted_timestamp,
                "sent_at": formatted_timestamp,
            }
            cursor = self._insert_dynamic(conn, "alerts", columns, values)
            return self._lastrowid(cursor)

    def insert_timeline(
        self,
        message: str,
        timestamp: Optional[datetime | str] = None,
    ) -> int:
        """Insert a timeline message and return its database id."""
        self.initialize()
        with self.connection() as conn:
            formatted_timestamp = self._format_timestamp(timestamp)
            columns = self._column_names(conn, "timeline")
            values: dict[str, Any] = {
                "message": message,
                "timestamp": formatted_timestamp,
                "file_path": message,
                "event_type": "timeline",
                "created_at": formatted_timestamp,
            }
            cursor = self._insert_dynamic(conn, "timeline", columns, values)
            return self._lastrowid(cursor)

    def get_events(
        self,
        file_path: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return events ordered from newest to oldest."""
        self.initialize()
        safe_limit = self._bounded_int(limit, default=100, minimum=1, maximum=1000)
        safe_offset = self._bounded_int(offset, default=0, minimum=0, maximum=1000000)
        query = """
            SELECT id, file_path, event_type, timestamp, severity, details
            FROM events
        """
        params: list[Any] = []

        if file_path is not None:
            query += " WHERE file_path = ?"
            params.append(file_path)

        query += " ORDER BY timestamp DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([safe_limit, safe_offset])

        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_last_snapshots(
        self,
        file_path: Optional[str] = None,
        limit: int = 2,
    ) -> list[dict[str, Any]]:
        """Return latest snapshots ordered from newest to oldest."""
        self.initialize()
        safe_limit = self._bounded_int(limit, default=2, minimum=1, maximum=1000)
        query = """
            SELECT id, file_path, hash, content, size, timestamp
            FROM snapshots
        """
        params: list[Any] = []

        if file_path is not None:
            query += " WHERE file_path = ?"
            params.append(file_path)

        query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
        params.append(safe_limit)

        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_snapshot(self, snapshot_id: int) -> Optional[dict[str, Any]]:
        """Return one snapshot by id."""
        self.initialize()
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT id, file_path, hash, content, size, timestamp
                FROM snapshots
                WHERE id = ?
                """,
                (snapshot_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)

    def list_snapshot_files(self) -> list[str]:
        """Return file paths that have stored snapshots."""
        self.initialize()
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT file_path
                FROM snapshots
                WHERE file_path != ''
                ORDER BY file_path ASC
                """
            ).fetchall()
            return [str(row["file_path"]) for row in rows]

    def get_timeline(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return timeline messages ordered from newest to oldest."""
        self.initialize()
        safe_limit = self._bounded_int(limit, default=100, minimum=1, maximum=1000)
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, message, timestamp
                FROM timeline
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_alerts(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return alerts ordered from newest to oldest."""
        self.initialize()
        safe_limit = self._bounded_int(limit, default=100, minimum=1, maximum=1000)
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, file_path, severity, reason, timestamp
                FROM alerts
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def _configure_connection(self, conn: Connection) -> None:
        """Configure SQLite pragmas for safer concurrent operation."""
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        with suppress(sqlite3.Error):
            conn.execute("PRAGMA journal_mode = WAL")

    def _ensure_compatibility_columns(self, conn: Connection) -> None:
        """Add missing columns when an older skeleton database already exists."""
        self._ensure_columns(
            conn,
            "events",
            {
                "file_path": "TEXT NOT NULL DEFAULT ''",
                "event_type": "TEXT NOT NULL DEFAULT ''",
                "timestamp": "TEXT NOT NULL DEFAULT ''",
                "severity": "TEXT NOT NULL DEFAULT 'INFO'",
                "details": "TEXT NOT NULL DEFAULT ''",
            },
        )
        self._ensure_columns(
            conn,
            "snapshots",
            {
                "file_path": "TEXT NOT NULL DEFAULT ''",
                "hash": "TEXT NOT NULL DEFAULT ''",
                "content": "TEXT NOT NULL DEFAULT ''",
                "size": "INTEGER NOT NULL DEFAULT 0",
                "timestamp": "TEXT NOT NULL DEFAULT ''",
            },
        )
        self._ensure_columns(
            conn,
            "alerts",
            {
                "file_path": "TEXT NOT NULL DEFAULT ''",
                "severity": "TEXT NOT NULL DEFAULT 'INFO'",
                "reason": "TEXT NOT NULL DEFAULT ''",
                "timestamp": "TEXT NOT NULL DEFAULT ''",
            },
        )
        self._ensure_columns(
            conn,
            "timeline",
            {
                "message": "TEXT NOT NULL DEFAULT ''",
                "timestamp": "TEXT NOT NULL DEFAULT ''",
            },
        )

    def _ensure_columns(
        self,
        conn: Connection,
        table: str,
        required_columns: dict[str, str],
    ) -> None:
        """Ensure a table contains required columns."""
        existing_columns = self._column_names(conn, table)
        for column, ddl in required_columns.items():
            if column not in existing_columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def _migrate_legacy_values(self, conn: Connection) -> None:
        """Copy values from old skeleton columns into the production schema."""
        self._copy_column(conn, "events", "created_at", "timestamp")
        self._copy_column(conn, "events", "reason", "details")
        self._copy_column(conn, "snapshots", "sha256", "hash")
        self._copy_column(conn, "snapshots", "size_bytes", "size")
        self._copy_column(conn, "snapshots", "created_at", "timestamp")
        self._copy_column(conn, "snapshots", "modified_at", "timestamp")
        self._copy_column(conn, "alerts", "message", "reason")
        self._copy_column(conn, "alerts", "sent_at", "timestamp")
        self._copy_column(conn, "timeline", "created_at", "timestamp")
        self._populate_legacy_timeline_messages(conn)

    def _copy_column(
        self,
        conn: Connection,
        table: str,
        source_column: str,
        target_column: str,
    ) -> None:
        """Copy non-empty legacy values into a new column when both exist."""
        columns = self._column_names(conn, table)
        if source_column not in columns or target_column not in columns:
            return

        conn.execute(
            f"""
            UPDATE {table}
            SET {target_column} = {source_column}
            WHERE ({target_column} IS NULL OR {target_column} = '')
              AND {source_column} IS NOT NULL
              AND {source_column} != ''
            """
        )

    def _populate_legacy_timeline_messages(self, conn: Connection) -> None:
        """Build timeline messages from old timeline file/event columns."""
        columns = self._column_names(conn, "timeline")
        if not {"message", "file_path", "event_type"} <= columns:
            return

        conn.execute(
            """
            UPDATE timeline
            SET message = file_path || ' ' || event_type
            WHERE (message IS NULL OR message = '')
            """
        )

    def _create_indexes(self, conn: Connection) -> None:
        """Create indexes for file and time lookups."""
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_events_file_path
                ON events(file_path);
            CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_snapshots_file_path
                ON snapshots(file_path);
            CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
                ON snapshots(timestamp);
            CREATE INDEX IF NOT EXISTS idx_alerts_file_path
                ON alerts(file_path);
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
                ON alerts(timestamp);
            CREATE INDEX IF NOT EXISTS idx_timeline_timestamp
                ON timeline(timestamp);
            """
        )

    @staticmethod
    def _insert_dynamic(
        conn: Connection,
        table: str,
        existing_columns: set[str],
        values: dict[str, Any],
    ) -> sqlite3.Cursor:
        """Insert values only for columns that exist in the current table."""
        insert_columns = [
            column for column in values if column in existing_columns
        ]
        placeholders = ", ".join("?" for _ in insert_columns)
        column_sql = ", ".join(insert_columns)
        return conn.execute(
            f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
            [values[column] for column in insert_columns],
        )

    @staticmethod
    def _column_names(conn: Connection, table: str) -> set[str]:
        """Return column names for a SQLite table."""
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {str(row["name"]) for row in rows}

    @staticmethod
    def _format_timestamp(value: Optional[datetime | str]) -> str:
        """Return an ISO-8601 UTC timestamp string."""
        if value is None or value == "":
            return datetime.now(tz=timezone.utc).isoformat()

        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).isoformat()

        return value

    @staticmethod
    def _bounded_int(
        value: int,
        default: int,
        minimum: int,
        maximum: int,
    ) -> int:
        """Return an integer constrained to a safe range."""
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default

        return min(max(parsed, minimum), maximum)

    @staticmethod
    def _row_to_dict(row: Row) -> dict[str, Any]:
        """Convert a sqlite3 row to a plain dictionary."""
        return dict(row)

    @staticmethod
    def _lastrowid(cursor: sqlite3.Cursor) -> int:
        """Return a guaranteed integer row id from an insert cursor."""
        lastrowid = cursor.lastrowid
        if lastrowid is None:
            raise DatabaseError("SQLite insert did not return a row id")

        return int(lastrowid)
