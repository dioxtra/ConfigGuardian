"""Timeline query service."""

from datetime import datetime, timezone
from typing import Any

from configguardian.core.database import Database
from configguardian.models.event_model import Event
from configguardian.utils.logger import get_logger


class TimelineService:
    """Read file activity timeline data."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.logger = get_logger(__name__)

    def list_events(self, limit: int = 100) -> list[Event]:
        """Return timeline events in reverse chronological order."""
        events: list[Event] = []

        for row in self.database.get_events(limit=limit):
            try:
                events.append(self._row_to_event(row))
            except (TypeError, ValueError) as exc:
                self.logger.exception("Skipping invalid event row %s: %s", row, exc)

        return events

    def _row_to_event(self, row: dict[str, Any]) -> Event:
        """Convert a database event row to the public event model."""
        return Event(
            id=self._optional_int(row.get("id")),
            file_path=str(row.get("file_path", "")),
            event_type=str(row.get("event_type", "")),
            severity=str(row.get("severity", "INFO")),
            reason=str(row.get("details", "")),
            created_at=self._parse_timestamp(row.get("timestamp")),
        )

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        """Convert a value to int when present."""
        if value is None:
            return None
        return int(value)

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        """Parse a timestamp into an aware datetime."""
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value

        if isinstance(value, str) and value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed

        return datetime.now(tz=timezone.utc)

