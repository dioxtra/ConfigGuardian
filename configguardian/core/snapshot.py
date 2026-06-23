"""Snapshot creation service."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from configguardian.core.database import Database
from configguardian.core.hashing import sha256_file
from configguardian.models.snapshot_model import Snapshot
from configguardian.utils.constants import DEFAULT_WATCHED_FILES
from configguardian.utils.logger import get_logger


class SnapshotService:
    """Create file snapshots and persist them."""

    def __init__(
        self,
        database: Database,
        watched_files: Optional[list[Path | str]] = None,
    ) -> None:
        self.database = database
        self.watched_files = [
            Path(path) for path in (watched_files or list(DEFAULT_WATCHED_FILES))
        ]
        self.logger = get_logger(__name__)

    def create_for_file(self, path: Path) -> Snapshot:
        """Build a snapshot model for one file."""
        stat = path.stat()
        return Snapshot(
            id=None,
            file_path=str(path),
            sha256=sha256_file(path),
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            content=path.read_text(encoding="utf-8", errors="replace"),
            created_at=datetime.now(tz=timezone.utc),
        )

    def create_all(self) -> list[int]:
        """Create snapshots for configured files."""
        snapshot_ids: list[int] = []

        for path in self.watched_files:
            try:
                if not path.exists() or not path.is_file():
                    self.logger.warning("Skipping missing watched file: %s", path)
                    continue

                snapshot = self.create_for_file(path)
                snapshot_id = self.database.insert_snapshot(
                    file_path=snapshot.file_path,
                    file_hash=snapshot.sha256,
                    content=snapshot.content,
                    size=snapshot.size_bytes,
                    timestamp=snapshot.created_at,
                )
                snapshot_ids.append(snapshot_id)
                self.database.insert_timeline(f"Snapshot created for {path}")
            except (OSError, PermissionError) as exc:
                self.logger.exception("Failed to snapshot %s: %s", path, exc)

        return snapshot_ids

