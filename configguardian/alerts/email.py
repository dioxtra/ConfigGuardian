"""SMTP email notifier."""

from email.message import EmailMessage
import smtplib
from typing import Optional

from configguardian.alerts.base import BaseNotifier


class EmailNotifier(BaseNotifier):
    """Send alerts by email using SMTP."""

    def __init__(
        self,
        smtp_host: str,
        sender: str,
        recipient: str,
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
        enabled: bool = True,
        timeout_seconds: float = 10.0,
    ) -> None:
        super().__init__(enabled=enabled)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender
        self.recipient = recipient
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.timeout_seconds = timeout_seconds

    def send(self, alert: dict[str, str]) -> None:
        """Send an email alert."""
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = self.recipient
        message["Subject"] = (
            f"ConfigGuardian {alert.get('severity', 'LOW')} alert: "
            f"{alert.get('file_path', '')}"
        )
        message.set_content(self._format_message(alert))

        with smtplib.SMTP(
            self.smtp_host,
            self.smtp_port,
            timeout=self.timeout_seconds,
        ) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username is not None and self.password is not None:
                smtp.login(self.username, self.password)
            smtp.send_message(message)

    @staticmethod
    def _format_message(alert: dict[str, str]) -> str:
        """Format an alert for email."""
        return (
            f"⚠ {alert.get('severity', 'LOW')} Severity\n\n"
            f"File: {alert.get('file_path', '')}\n\n"
            f"Reason: {alert.get('reason', '')}\n\n"
            f"Recommendation: {alert.get('recommendation', '')}\n\n"
            f"Time: {alert.get('timestamp', '')}"
        )

