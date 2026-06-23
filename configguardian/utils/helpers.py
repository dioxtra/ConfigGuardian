"""General-purpose helpers."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(tz=timezone.utc)

