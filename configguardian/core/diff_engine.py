"""Snapshot diff engine."""

from dataclasses import dataclass
import difflib
from typing import Any, Optional

from configguardian.core.database import Database
from configguardian.utils.logger import get_logger


@dataclass(frozen=True)
class DiffResult:
    """Human-readable diff summary for one file."""

    file_path: str
    summary: str
    added_lines: list[str]
    removed_lines: list[str]
    changed_lines: list[str]


class DiffEngine:
    """Compare stored snapshots."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.logger = get_logger(__name__)

    def compare(
        self,
        old_snapshot_id: Optional[int],
        new_snapshot_id: Optional[int],
    ) -> list[DiffResult]:
        """Compare snapshots and return structured diff results."""
        if old_snapshot_id is not None and new_snapshot_id is not None:
            return self._compare_snapshot_ids(old_snapshot_id, new_snapshot_id)

        return self._compare_latest_per_file()

    def _compare_snapshot_ids(
        self,
        old_snapshot_id: int,
        new_snapshot_id: int,
    ) -> list[DiffResult]:
        """Compare two explicit snapshot ids."""
        old_snapshot = self.database.get_snapshot(old_snapshot_id)
        new_snapshot = self.database.get_snapshot(new_snapshot_id)

        if old_snapshot is None or new_snapshot is None:
            self.logger.warning(
                "Cannot diff missing snapshots: old=%s new=%s",
                old_snapshot_id,
                new_snapshot_id,
            )
            return []

        return [self._build_diff(old_snapshot, new_snapshot)]

    def _compare_latest_per_file(self) -> list[DiffResult]:
        """Compare the latest two snapshots for each file."""
        results: list[DiffResult] = []

        for file_path in self.database.list_snapshot_files():
            snapshots = self.database.get_last_snapshots(file_path=file_path, limit=2)
            if len(snapshots) < 2:
                continue

            newer, older = snapshots[0], snapshots[1]
            results.append(self._build_diff(older, newer))

        return results

    def _build_diff(
        self,
        old_snapshot: dict[str, Any],
        new_snapshot: dict[str, Any],
    ) -> DiffResult:
        """Build a structured diff result from two snapshot rows."""
        old_lines = str(old_snapshot.get("content", "")).splitlines()
        new_lines = str(new_snapshot.get("content", "")).splitlines()
        added_lines: list[str] = []
        removed_lines: list[str] = []
        changed_lines: list[str] = []

        for line in difflib.ndiff(old_lines, new_lines):
            marker = line[:2]
            value = line[2:]
            if marker == "+ ":
                added_lines.append(value)
            elif marker == "- ":
                removed_lines.append(value)
            elif marker == "? ":
                changed_lines.append(value)

        summary = (
            f"{len(added_lines)} added, "
            f"{len(removed_lines)} removed, "
            f"{len(changed_lines)} changed"
        )

        return DiffResult(
            file_path=str(new_snapshot.get("file_path", "")),
            summary=summary,
            added_lines=added_lines,
            removed_lines=removed_lines,
            changed_lines=changed_lines,
        )

