"""Real-time file monitoring engine for ConfigGuardian."""

import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from time import monotonic
from typing import Any, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from configguardian.alerts.manager import AlertManager
from configguardian.core.analyzer import AnalyzerEngine
from configguardian.core.database import Database
from configguardian.utils.constants import DEFAULT_WATCHED_FILES
from configguardian.utils.logger import get_logger


class MonitorEventHandler(FileSystemEventHandler):
    """Translate watchdog file events into ConfigGuardian database events."""

    def __init__(self, monitor: "Monitor") -> None:
        self.monitor = monitor

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        self.monitor.handle_event(event, "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        self.monitor.handle_event(event, "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        self.monitor.handle_event(event, "deleted")


class Monitor:
    """Watch configured files and persist file events to SQLite."""

    def __init__(
        self,
        database: Database,
        config_path: Optional[Path | str] = None,
        watched_paths: Optional[list[Path | str]] = None,
        observer: Optional[BaseObserver] = None,
        analyzer_engine: Optional[AnalyzerEngine] = None,
        alert_manager: Optional[AlertManager] = None,
        debounce_seconds: float = 1.0,
    ) -> None:
        self.database = database
        self.config_path = Path(config_path) if config_path is not None else None
        self.logger = get_logger(__name__)
        self.observer = observer or Observer()
        self.analyzer_engine = analyzer_engine
        self.alert_manager = alert_manager
        self.debounce_seconds = debounce_seconds
        self._lock = RLock()
        self._running = False
        self._watched_files = self._load_watched_files(watched_paths)
        self._last_event_at: dict[tuple[str, str], float] = {}

    def start(self) -> None:
        """Start watchdog monitoring in the background."""
        with self._lock:
            if self._running:
                self.logger.info("ConfigGuardian monitor is already running")
                return

            try:
                self.database.initialize()
                handler = MonitorEventHandler(self)

                scheduled_directories = 0
                for directory in self._watch_directories():
                    try:
                        self.observer.schedule(
                            handler,
                            str(directory),
                            recursive=False,
                        )
                        scheduled_directories += 1
                    except Exception as exc:  # watchdog can raise platform errors.
                        self.logger.exception(
                            "Failed to schedule directory %s: %s",
                            directory,
                            exc,
                        )

                if scheduled_directories == 0:
                    self.logger.warning("No existing directories available to monitor")
                    return

                self.observer.start()
                self._running = True
                self.logger.info(
                    "ConfigGuardian monitor started for %d file(s)",
                    len(self._watched_files),
                )
            except Exception as exc:
                self.logger.exception("Failed to start monitor: %s", exc)

    def stop(self) -> None:
        """Stop watchdog monitoring."""
        with self._lock:
            if not self._running:
                self.logger.info("ConfigGuardian monitor is not running")
                return

            try:
                self.observer.stop()
                self.observer.join()
                self.logger.info("ConfigGuardian monitor stopped")
            except Exception as exc:
                self.logger.exception("Failed to stop monitor: %s", exc)
            finally:
                self._running = False

    def handle_event(self, event: FileSystemEvent, event_type: str) -> None:
        """Persist a watchdog event if it targets a watched file."""
        if event.is_directory:
            return

        file_path = self._normalize_path(event.src_path)
        if file_path not in self._watched_files:
            return

        if self._is_debounced(file_path, event_type):
            return

        timestamp = datetime.now(tz=timezone.utc).isoformat()
        details = f"File {file_path} {event_type}"
        analyzer_event = {
            "file_path": file_path,
            "event_type": event_type,
            "details": details,
            "timestamp": timestamp,
            "content": self._safe_read_content(file_path, event_type),
        }

        try:
            self.database.insert_event(
                file_path=file_path,
                event_type=event_type,
                severity="INFO",
                details=details,
                timestamp=timestamp,
            )
            self.logger.info(details)
            self._analyze_and_alert(analyzer_event)
        except Exception as exc:
            self.logger.exception(
                "Failed to persist file event for %s: %s",
                file_path,
                exc,
            )

    def _load_watched_files(
        self,
        watched_paths: Optional[list[Path | str]],
    ) -> set[str]:
        """Load default, explicit, and YAML-configured watched files."""
        paths: set[str] = {
            self._normalize_path(path) for path in DEFAULT_WATCHED_FILES
        }

        if watched_paths is not None:
            paths.update(self._normalize_path(path) for path in watched_paths)

        paths.update(self._load_yaml_paths())
        return paths

    def _load_yaml_paths(self) -> set[str]:
        """Load extra watched paths from an optional YAML config file."""
        if self.config_path is None:
            return set()

        if not self.config_path.exists():
            self.logger.warning("Monitor config file does not exist: %s", self.config_path)
            return set()

        try:
            import yaml

            content = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            self.logger.exception(
                "Failed to load monitor config file %s: %s",
                self.config_path,
                exc,
            )
            return set()

        raw_paths = self._extract_paths_from_config(content)
        return {self._normalize_path(path) for path in raw_paths}

    def _extract_paths_from_config(self, content: Any) -> list[str]:
        """Extract watched file paths from supported YAML shapes."""
        if isinstance(content, list):
            return [str(item) for item in content]

        if not isinstance(content, dict):
            self.logger.warning("Monitor config must be a YAML mapping or list")
            return []

        paths: list[str] = []
        for key in ("watched_files", "extra_paths", "paths"):
            value = content.get(key)
            if isinstance(value, list):
                paths.extend(str(item) for item in value)

        return paths

    def _watch_directories(self) -> set[Path]:
        """Return existing parent directories for watched files."""
        directories: set[Path] = set()

        for file_path in self._watched_files:
            directory = Path(file_path).parent
            if directory.exists() and directory.is_dir():
                directories.add(directory)
            else:
                self.logger.warning(
                    "Skipping unavailable watch directory: %s",
                    directory,
                )

        return directories

    def _is_debounced(self, file_path: str, event_type: str) -> bool:
        """Return whether a duplicate event should be skipped."""
        event_key = (file_path, event_type)
        now = monotonic()
        last_seen = self._last_event_at.get(event_key)
        self._last_event_at[event_key] = now
        return last_seen is not None and now - last_seen < self.debounce_seconds

    def _safe_read_content(self, file_path: str, event_type: str) -> str:
        """Read changed file content when it is safe to do so."""
        if event_type == "deleted":
            return ""

        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                return path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self.logger.exception("Failed to read changed file %s: %s", file_path, exc)

        return ""

    def _analyze_and_alert(self, event: dict[str, str]) -> None:
        """Run optional analyzer and alert dispatch without breaking monitoring."""
        if self.analyzer_engine is None or self.alert_manager is None:
            return

        try:
            results = self.analyzer_engine.analyze(event)
            self.alert_manager.emit_results(results)
        except Exception as exc:
            self.logger.exception("Analyzer or alert dispatch failed: %s", exc)

    @staticmethod
    def _normalize_path(path: Path | str | bytes) -> str:
        """Normalize a path for exact event matching."""
        if isinstance(path, bytes):
            path = os.fsdecode(path)

        return str(Path(path).expanduser().resolve(strict=False))


def run_monitor(db: Database) -> Monitor:
    """Create and start a monitor for the provided database."""
    monitor = Monitor(database=db)
    monitor.start()
    return monitor


MonitorService = Monitor
