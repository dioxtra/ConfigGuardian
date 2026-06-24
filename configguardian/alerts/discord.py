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
        payload = {
            "content": f"@everyone\n{self.format_message(alert)}",
            "allowed_mentions": {"parse": ["everyone"]},
        }
        request = Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ConfigGuardian/0.1",
            },
            method="POST",
        )

        with urlopen(request, timeout=self.timeout_seconds) as response:
            response.read()
