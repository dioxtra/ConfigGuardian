"""Notification providers."""

from configguardian.alerts.base import BaseNotifier
from configguardian.alerts.discord import DiscordNotifier
from configguardian.alerts.email import EmailNotifier
from configguardian.alerts.manager import AlertManager
from configguardian.alerts.slack import SlackNotifier
from configguardian.alerts.telegram import TelegramNotifier

__all__ = [
    "AlertManager",
    "BaseNotifier",
    "DiscordNotifier",
    "EmailNotifier",
    "SlackNotifier",
    "TelegramNotifier",
]
