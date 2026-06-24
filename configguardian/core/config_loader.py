"""Load ConfigGuardian services from YAML-compatible configuration."""

from collections.abc import Mapping
from typing import Any

from configguardian.alerts.base import BaseNotifier
from configguardian.alerts.discord import DiscordNotifier
from configguardian.alerts.email import EmailNotifier
from configguardian.alerts.manager import AlertManager
from configguardian.alerts.slack import SlackNotifier
from configguardian.alerts.telegram import TelegramNotifier
from configguardian.utils.logger import get_logger

logger = get_logger(__name__)


def load_alert_manager_from_config(config: dict[str, Any]) -> AlertManager:
    """Build an alert manager from a YAML-loaded configuration mapping."""
    alerts_config = config.get("alerts")
    if not isinstance(alerts_config, Mapping):
        return AlertManager()

    manager_config = {
        "min_severity": alerts_config.get("min_severity", "MEDIUM"),
        "cooldown_seconds": alerts_config.get("cooldown_seconds", 30),
        "send_low": alerts_config.get("send_low", False),
        "send_all_results": alerts_config.get("send_all_results", False),
    }
    manager = AlertManager(config=manager_config)

    providers_config = alerts_config.get("providers")
    if not isinstance(providers_config, Mapping):
        return manager

    for provider_name, provider_config in providers_config.items():
        notifier = _build_notifier(str(provider_name), provider_config)
        if notifier is not None:
            manager.register(notifier)

    return manager


def _build_notifier(provider_name: str, provider_config: Any) -> BaseNotifier | None:
    """Create a notifier from a provider config mapping."""
    if not isinstance(provider_config, Mapping):
        logger.warning(
            "Skipping provider %s because its configuration is invalid.",
            provider_name,
        )
        return None

    if not _is_enabled(provider_config.get("enabled", False)):
        return None

    builder = _PROVIDER_BUILDERS.get(provider_name.lower())
    if builder is None:
        logger.warning("Skipping unknown alert provider: %s", provider_name)
        return None

    try:
        return builder(provider_config)
    except ValueError as exc:
        logger.warning("Skipping provider %s: %s", provider_name, exc)
        return None


def _build_discord_notifier(provider_config: Mapping[str, Any]) -> DiscordNotifier:
    """Build a Discord notifier from config."""
    webhook_url = _required_string(provider_config, "webhook_url", "discord")
    timeout_seconds = float(provider_config.get("timeout_seconds", 10.0))
    return DiscordNotifier(
        webhook_url=webhook_url,
        enabled=True,
        timeout_seconds=timeout_seconds,
    )


def _build_telegram_notifier(provider_config: Mapping[str, Any]) -> TelegramNotifier:
    """Build a Telegram notifier from config."""
    bot_token = _required_string(provider_config, "bot_token", "telegram")
    chat_id = _required_string(provider_config, "chat_id", "telegram")
    timeout_seconds = float(provider_config.get("timeout_seconds", 10.0))
    return TelegramNotifier(
        bot_token=bot_token,
        chat_id=chat_id,
        enabled=True,
        timeout_seconds=timeout_seconds,
    )


def _build_slack_notifier(provider_config: Mapping[str, Any]) -> SlackNotifier:
    """Build a Slack notifier from config."""
    webhook_url = _required_string(provider_config, "webhook_url", "slack")
    timeout_seconds = float(provider_config.get("timeout_seconds", 10.0))
    return SlackNotifier(
        webhook_url=webhook_url,
        enabled=True,
        timeout_seconds=timeout_seconds,
    )


def _build_email_notifier(provider_config: Mapping[str, Any]) -> EmailNotifier:
    """Build an email notifier from config."""
    smtp_host = _required_string(provider_config, "smtp_host", "email")
    sender = _required_string(provider_config, "sender", "email")
    recipient = _required_string(provider_config, "recipient", "email")

    smtp_port = int(provider_config.get("smtp_port", 587))
    timeout_seconds = float(provider_config.get("timeout_seconds", 10.0))
    username = _optional_string(provider_config.get("username"))
    password = _optional_string(provider_config.get("password"))
    use_tls = _is_enabled(provider_config.get("use_tls", True))

    return EmailNotifier(
        smtp_host=smtp_host,
        sender=sender,
        recipient=recipient,
        smtp_port=smtp_port,
        username=username,
        password=password,
        use_tls=use_tls,
        enabled=True,
        timeout_seconds=timeout_seconds,
    )


def _required_string(
    provider_config: Mapping[str, Any],
    key: str,
    provider_name: str,
) -> str:
    """Return a required non-empty string value or raise a validation error."""
    value = provider_config.get(key)
    if value is None or str(value).strip() == "":
        raise ValueError(f"missing required field '{key}'")
    return str(value)


def _optional_string(value: Any) -> str | None:
    """Return a string value or None when the input is empty."""
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _is_enabled(value: Any) -> bool:
    """Return a permissive boolean for YAML-derived values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


_PROVIDER_BUILDERS = {
    "discord": _build_discord_notifier,
    "telegram": _build_telegram_notifier,
    "slack": _build_slack_notifier,
    "email": _build_email_notifier,
}
