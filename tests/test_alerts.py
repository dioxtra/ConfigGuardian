"""Alert manager tests."""

import json

from configguardian.alerts.base import BaseNotifier
from configguardian.alerts.discord import DiscordNotifier
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


def test_discord_notifier_mentions_everyone(monkeypatch) -> None:
    """Discord payload includes an explicit everyone mention."""
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b""

    def fake_urlopen(request, timeout: float):
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("configguardian.alerts.discord.urlopen", fake_urlopen)

    notifier = DiscordNotifier("https://discord.com/api/webhooks/test")
    notifier.send(
        {
            "file_path": "/tmp/app.conf",
            "severity": "HIGH",
            "reason": "Test",
            "recommendation": "Review",
            "timestamp": "2026-06-23T21:10:00+00:00",
        }
    )

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert str(payload["content"]).startswith("@everyone\n")
    assert payload["allowed_mentions"] == {"parse": ["everyone"]}
