"""JSON report generator."""

from pathlib import Path
import json

from configguardian.core.database import Database


class JsonReport:
    """Generate JSON reports."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def generate(self, output_path: Path) -> Path:
        """Generate a JSON report."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "events": self.database.get_events(limit=100),
            "snapshots": self.database.get_last_snapshots(limit=100),
            "alerts": self.database.get_alerts(limit=100),
        }
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path

