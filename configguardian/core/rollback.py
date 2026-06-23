"""Rollback service."""

from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any

from configguardian.core.database import Database
from configguardian.utils.constants import BACKUP_SUFFIX
from configguardian.utils.logger import get_logger


class RollbackService:
    """Restore file content from a stored snapshot."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.logger = get_logger(__name__)

    def restore(self, snapshot_id: int) -> Path:
        """Restore snapshot content and return backup path."""
        snapshot = self.database.get_snapshot(snapshot_id)
        if snapshot is None:
            raise ValueError(f"Snapshot not found: {snapshot_id}")

        target_path = Path(str(snapshot.get("file_path", "")))
        if not str(target_path):
            raise ValueError(f"Snapshot {snapshot_id} does not include a file path")

        backup_path = self._backup_path(target_path)
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if target_path.exists():
                shutil.copy2(target_path, backup_path)
            else:
                backup_path.write_text("", encoding="utf-8")

            content = str(snapshot.get("content", ""))
            target_path.write_text(content, encoding="utf-8")
            self.database.insert_timeline(f"Rollback restored {target_path}")
            return backup_path
        except OSError as exc:
            self.logger.exception(
                "Failed to rollback snapshot %s to %s: %s",
                snapshot_id,
                target_path,
                exc,
            )
            raise

    def _backup_path(self, target_path: Path) -> Path:
        """Return a timestamped backup path for a rollback target."""
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
        return target_path.with_name(f"{target_path.name}.{timestamp}{BACKUP_SUFFIX}")

