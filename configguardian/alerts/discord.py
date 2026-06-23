"""Discord webhook notifier."""

import json
from urllib.request import Request, urlopen

from configguardian.alerts.base import BaseNotifier


class DiscordNotifier(BaseNotifier):
    """Send alerts to Discord using an incoming webhook."""

    def __init__(
        self,
        webhook_url: str,
        enabled: bool = True,
        timeout_seconds: float = 10.0,
    ) -> None:
        super().__init__(enabled=enabled)
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds

    def send(self, alert: dict[str, str]) -> None:
        """Send a Discord alert."""
        payload = {"content": self._format_message(alert)}
        request = Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(request, timeout=self.timeout_seconds) as response:
            response.read()

    @staticmethod
    def _format_message(alert: dict[str, str]) -> str:
        """Format an alert for Discord."""
        return (
            f"⚠ {alert.get('severity', 'LOW')} Severity\n\n"
            f"File: {alert.get('file_path', '')}\n\n"
            f"Reason: {alert.get('reason', '')}\n\n"
            f"Recommendation: {alert.get('recommendation', '')}\n\n"
            f"Time: {alert.get('timestamp', '')}"
        )

