"""Telegram notifier."""

import json
from urllib.request import Request, urlopen

from configguardian.alerts.base import BaseNotifier


class TelegramNotifier(BaseNotifier):
    """Send alerts through Telegram Bot API."""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        enabled: bool = True,
        timeout_seconds: float = 10.0,
    ) -> None:
        super().__init__(enabled=enabled)
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout_seconds = timeout_seconds

    def send(self, alert: dict[str, str]) -> None:
        """Send a Telegram alert."""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": self._format_message(alert),
            "disable_web_page_preview": True,
        }
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(request, timeout=self.timeout_seconds) as response:
            response.read()

    @staticmethod
    def _format_message(alert: dict[str, str]) -> str:
        """Format an alert for Telegram."""
        return (
            f"⚠ {alert.get('severity', 'LOW')} Severity\n\n"
            f"File: {alert.get('file_path', '')}\n\n"
            f"Reason: {alert.get('reason', '')}\n\n"
            f"Recommendation: {alert.get('recommendation', '')}\n\n"
            f"Time: {alert.get('timestamp', '')}"
        )
