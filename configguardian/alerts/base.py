"""Base notifier contract for ConfigGuardian alerts."""

from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    """Base class for all alert notification providers."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    @abstractmethod
    def send(self, alert: dict[str, str]) -> None:
        """Send an alert payload."""

