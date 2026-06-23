"""Alert manager tests."""

from configguardian.alerts.base import BaseNotifier
from configguardian.alerts.manager import AlertManager


class FakeNotifier(BaseNotifier):
    """Collect alerts instead of sending them."""

    def __init__(self) -> None:
        super().__init__()
        self.alerts: list[dict[str, str]] = []

    def send(self, alert: dict[str, str]) -> None:
        """Store an alert."""
        self.alerts.append(alert)


def test_alert_manager_filters_low_alerts() -> None:
    """LOW alerts are ignored by default."""
    notifier = FakeNotifier()
    manager = AlertManager(notifiers=[notifier])

    manager.emit(
        {
            "file_path": "/tmp/app.conf",
            "severity": "LOW",
            "reason": "Generic change",
            "recommendation": "Review",
            "timestamp": "2026-06-23T21:10:00+00:00",
        }
    )

    assert notifier.alerts == []


def test_alert_manager_sends_medium_and_deduplicates() -> None:
    """MEDIUM alerts are sent once and duplicates are suppressed."""
    notifier = FakeNotifier()
    manager = AlertManager(
        config={"cooldown_seconds": 30},
        notifiers=[notifier],
    )
    alert = {
        "file_path": "/tmp/app.conf",
        "severity": "MEDIUM",
        "reason": "Cron changed",
        "recommendation": "Review cron",
        "timestamp": "2026-06-23T21:10:00+00:00",
    }

    manager.emit(alert)
    manager.emit(alert)
    manager.shutdown()

    assert len(notifier.alerts) == 1
