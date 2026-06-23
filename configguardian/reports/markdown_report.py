"""Markdown report generator."""

from pathlib import Path

from configguardian.core.database import Database


class MarkdownReport:
    """Generate Markdown reports."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def generate(self, output_path: Path) -> Path:
        """Generate a Markdown report."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        events = self.database.get_events(limit=100)
        snapshots = self.database.get_last_snapshots(limit=100)
        lines = [
            "# ConfigGuardian Report",
            "",
            f"- Events: {len(events)}",
            f"- Snapshots: {len(snapshots)}",
            "",
            "## Recent Events",
            "",
        ]

        if events:
            for event in events:
                lines.append(
                    "- "
                    f"{event.get('timestamp', '')} "
                    f"{event.get('file_path', '')} "
                    f"{event.get('event_type', '')} "
                    f"({event.get('severity', '')})"
                )
        else:
            lines.append("- No events recorded.")

        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return output_path

