"""Alert manager for analyzer results and notifier dispatch."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import RLock
from time import monotonic
from typing import Optional

from configguardian.alerts.base import BaseNotifier
from configguardian.utils.logger import get_logger


class AlertManager:
    """Filter, group, and dispatch security alerts."""

    SEVERITY_ORDER = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    def __init__(
        self,
        config: Optional[dict[str, object]] = None,
        notifiers: Optional[list[BaseNotifier]] = None,
    ) -> None:
        self.config = config or {}
        self.min_severity = str(self.config.get("min_severity", "MEDIUM")).upper()
        self.cooldown_seconds = int(self.config.get("cooldown_seconds", 30))
        self.send_low = bool(self.config.get("send_low", False))
        self.send_all_results = bool(self.config.get("send_all_results", False))
        self.max_workers = int(self.config.get("max_workers", 4))
        self.notifiers: list[BaseNotifier] = notifiers or []
        self.logger = get_logger(__name__)
        self._last_sent_by_file: dict[str, float] = {}
        self._last_fingerprint_by_file: dict[str, str] = {}
        self._grouped_counts_by_file: dict[str, int] = {}
        self._lock = RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, self.max_workers),
            thread_name_prefix="configguardian-alert",
        )

    def register(self, notifier: BaseNotifier) -> None:
        """Register a notifier."""
        with self._lock:
            self.notifiers.append(notifier)

    def emit(self, alert: dict[str, str]) -> None:
        """Dispatch one normalized alert to enabled notifiers."""
        normalized = self._normalize_alert(alert)

        with self._lock:
            if not self.should_send(normalized):
                self._group_alert(normalized)
                return

            grouped_count = self._grouped_counts_by_file.pop(
                normalized["file_path"],
                0,
            )
            if grouped_count:
                normalized["reason"] = (
                    f"{normalized['reason']} "
                    f"({grouped_count} related alert(s) grouped during cooldown)"
                )

            notifiers = [notifier for notifier in self.notifiers if notifier.enabled]
            file_path = normalized["file_path"]
            self._last_sent_by_file[file_path] = monotonic()
            self._last_fingerprint_by_file[file_path] = self._fingerprint(normalized)

        for notifier in notifiers:
            self._executor.submit(self._send_safely, notifier, normalized.copy())

    def emit_results(self, results: list[dict[str, str]]) -> None:
        """Dispatch analyzer results according to manager configuration."""
        selected_results = results if self.send_all_results else self._worst_only(results)

        for result in selected_results:
            self.emit(result)

    def should_send(self, alert: dict[str, str]) -> bool:
        """Return whether an alert should be sent now."""
        severity = alert.get("severity", "LOW").upper()
        if severity == "LOW" and not self.send_low:
            return False

        if self._severity_score(severity) < self._severity_score(self.min_severity):
            return False

        file_path = alert.get("file_path", "")
        fingerprint = self._fingerprint(alert)

        if self._last_fingerprint_by_file.get(file_path) == fingerprint:
            return False

        last_sent = self._last_sent_by_file.get(file_path)
        if last_sent is None:
            return True

        return monotonic() - last_sent >= self.cooldown_seconds

    def shutdown(self) -> None:
        """Stop background alert workers after queued sends finish."""
        self._executor.shutdown(wait=True)

    def _send_safely(self, notifier: BaseNotifier, alert: dict[str, str]) -> None:
        """Send through a notifier and log failures."""
        try:
            notifier.send(alert)
        except Exception as exc:
            self.logger.exception(
                "Failed to send alert via %s: %s",
                notifier.__class__.__name__,
                exc,
            )

    def _group_alert(self, alert: dict[str, str]) -> None:
        """Track alerts suppressed during cooldown."""
        severity = alert.get("severity", "LOW").upper()
        if severity == "LOW" and not self.send_low:
            return

        if self._severity_score(severity) < self._severity_score(self.min_severity):
            return

        file_path = alert.get("file_path", "")
        self._grouped_counts_by_file[file_path] = (
            self._grouped_counts_by_file.get(file_path, 0) + 1
        )

    def _normalize_alert(self, alert: dict[str, str]) -> dict[str, str]:
        """Return an alert with all required fields."""
        return {
            "file_path": alert.get("file_path", ""),
            "severity": alert.get("severity", "LOW").upper(),
            "reason": alert.get("reason", "Security event detected"),
            "recommendation": alert.get(
                "recommendation",
                "Review and validate this configuration change.",
            ),
            "timestamp": alert.get("timestamp", self._utc_timestamp()),
        }

    def _worst_only(self, results: list[dict[str, str]]) -> list[dict[str, str]]:
        """Return a one-item list containing the highest-severity result."""
        if not results:
            return []

        return [
            max(
                results,
                key=lambda result: self._severity_score(result.get("severity", "LOW")),
            )
        ]

    def _severity_score(self, severity: str) -> int:
        """Return a numeric severity score."""
        return self.SEVERITY_ORDER.get(severity.upper(), 0)

    @staticmethod
    def _fingerprint(alert: dict[str, str]) -> str:
        """Return a stable duplicate key for an alert."""
        return "|".join(
            (
                alert.get("file_path", ""),
                alert.get("severity", ""),
                alert.get("reason", ""),
                alert.get("recommendation", ""),
            )
        )

    @staticmethod
    def _utc_timestamp() -> str:
        """Return the current UTC timestamp in ISO format."""
        return datetime.now(tz=timezone.utc).isoformat()
