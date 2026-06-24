"""Tests for YAML-based alert manager loading."""

from configguardian.alerts.discord import DiscordNotifier
from configguardian.alerts.manager import AlertManager
from configguardian.core.config_loader import load_alert_manager_from_config


def test_load_alert_manager_no_alerts_key() -> None:
    """Missing alerts key returns an empty alert manager."""
    manager = load_alert_manager_from_config({})

    assert isinstance(manager, AlertManager)
    assert manager.notifiers == []


def test_load_alert_manager_discord_enabled() -> None:
    """Enabled Discord config creates a Discord notifier."""
    manager = load_alert_manager_from_config(
        {
            "alerts": {
                "providers": {
                    "discord": {
                        "enabled": True,
                        "webhook_url": "https://discord.com/api/webhooks/test",
                    }
                }
            }
        }
    )

    assert len(manager.notifiers) == 1
    assert isinstance(manager.notifiers[0], DiscordNotifier)


def test_load_alert_manager_skips_disabled_providers() -> None:
    """Disabled providers are ignored."""
    manager = load_alert_manager_from_config(
        {
            "alerts": {
                "providers": {
                    "discord": {
                        "enabled": False,
                        "webhook_url": "https://discord.com/api/webhooks/test",
                    },
                    "telegram": {
                        "enabled": False,
                        "bot_token": "token",
                        "chat_id": "chat",
                    },
                }
            }
        }
    )

    assert manager.notifiers == []


def test_load_alert_manager_skips_missing_required_field() -> None:
    """Missing required fields skip the provider without raising."""
    manager = load_alert_manager_from_config(
        {
            "alerts": {
                "providers": {
                    "discord": {
                        "enabled": True,
                    }
                }
            }
        }
    )

    assert manager.notifiers == []
