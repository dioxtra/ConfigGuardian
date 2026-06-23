"""HTML report generator."""

from collections import Counter
from html import escape
from pathlib import Path

from configguardian.core.database import Database
from configguardian.utils.constants import DEFAULT_REPORT_PATH


class HtmlReport:
    """Generate Bootstrap-based HTML reports."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def generate(self, output_path: Path = DEFAULT_REPORT_PATH) -> Path:
        """Generate an HTML report and return its path."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        events = self.database.get_events(limit=100)
        snapshots = self.database.get_last_snapshots(limit=100)
        severity_counts = Counter(str(event.get("severity", "INFO")) for event in events)
        file_counts = Counter(str(snapshot.get("file_path", "")) for snapshot in snapshots)

        output_path.write_text(
            self._render(events, snapshots, severity_counts, file_counts),
            encoding="utf-8",
        )
        return output_path

    def _render(
        self,
        events: list[dict[str, object]],
        snapshots: list[dict[str, object]],
        severity_counts: Counter[str],
        file_counts: Counter[str],
    ) -> str:
        """Render report HTML."""
        event_rows = "\n".join(
            "<tr>"
            f"<td>{escape(str(event.get('timestamp', '')))}</td>"
            f"<td>{escape(str(event.get('file_path', '')))}</td>"
            f"<td>{escape(str(event.get('event_type', '')))}</td>"
            f"<td>{escape(str(event.get('severity', '')))}</td>"
            f"<td>{escape(str(event.get('details', '')))}</td>"
            "</tr>"
            for event in events
        )
        severity_rows = "\n".join(
            f"<tr><td>{escape(severity)}</td><td>{count}</td></tr>"
            for severity, count in severity_counts.items()
        )
        file_rows = "\n".join(
            f"<tr><td>{escape(path)}</td><td>{count}</td></tr>"
            for path, count in file_counts.items()
            if path
        )
        latest_rows = "\n".join(
            "<tr>"
            f"<td>{escape(str(snapshot.get('id', '')))}</td>"
            f"<td>{escape(str(snapshot.get('file_path', '')))}</td>"
            f"<td>{escape(str(snapshot.get('hash', '')))}</td>"
            f"<td>{escape(str(snapshot.get('size', '')))}</td>"
            f"<td>{escape(str(snapshot.get('timestamp', '')))}</td>"
            "</tr>"
            for snapshot in snapshots[:10]
        )

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ConfigGuardian Report</title>
  <link
    href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
    rel="stylesheet"
  >
</head>
<body class="bg-light">
  <main class="container py-4">
    <h1 class="mb-4">ConfigGuardian Report</h1>
    <div class="row g-3 mb-4">
      <div class="col-md-4">
        <div class="card"><div class="card-body">
          <h2 class="h5">Events</h2><p class="display-6">{len(events)}</p>
        </div></div>
      </div>
      <div class="col-md-4">
        <div class="card"><div class="card-body">
          <h2 class="h5">Snapshots</h2><p class="display-6">{len(snapshots)}</p>
        </div></div>
      </div>
      <div class="col-md-4">
        <div class="card"><div class="card-body">
          <h2 class="h5">Files</h2><p class="display-6">{len(file_counts)}</p>
        </div></div>
      </div>
    </div>

    <h2 class="h4">Severity Distribution</h2>
    <table class="table table-sm table-striped">
      <thead><tr><th>Severity</th><th>Count</th></tr></thead>
      <tbody>{severity_rows or '<tr><td colspan="2">No events</td></tr>'}</tbody>
    </table>

    <h2 class="h4">Recent Events</h2>
    <table class="table table-sm table-striped">
      <thead>
        <tr><th>Time</th><th>File</th><th>Event</th><th>Severity</th><th>Details</th></tr>
      </thead>
      <tbody>{event_rows or '<tr><td colspan="5">No events</td></tr>'}</tbody>
    </table>

    <h2 class="h4">Latest Snapshots</h2>
    <table class="table table-sm table-striped">
      <thead>
        <tr><th>ID</th><th>File</th><th>Hash</th><th>Size</th><th>Time</th></tr>
      </thead>
      <tbody>{latest_rows or '<tr><td colspan="5">No snapshots</td></tr>'}</tbody>
    </table>

    <h2 class="h4">File Statistics</h2>
    <table class="table table-sm table-striped">
      <thead><tr><th>File</th><th>Snapshots</th></tr></thead>
      <tbody>{file_rows or '<tr><td colspan="2">No snapshots</td></tr>'}</tbody>
    </table>
  </main>
</body>
</html>
"""

