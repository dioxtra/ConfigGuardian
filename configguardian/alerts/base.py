"""Base notifier contract for ConfigGuardian alerts."""

from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    """Base class for all alert notification providers."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def format_message(self, alert: dict[str, str]) -> str:
        """Format a standard alert message for text-based providers."""
        return (
            f"⚠ {alert.get('severity', 'LOW')} Severity\n\n"
            f"File: {alert.get('file_path', '')}\n\n"
            f"Reason: {alert.get('reason', '')}\n\n"
            f"Recommendation: {alert.get('recommendation', '')}\n\n"
            f"Time: {alert.get('timestamp', '')}"
        )

    @abstractmethod
    def send(self, alert: dict[str, str]) -> None:
        """Send an alert payload."""
