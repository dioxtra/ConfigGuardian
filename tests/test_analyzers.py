"""Analyzer smoke tests."""

from pathlib import Path

from configguardian.analyzers.cron import CronAnalyzer
from configguardian.analyzers.ssh import SshAnalyzer
from configguardian.core.analyzer import create_default_engine


def test_ssh_analyzer_flags_root_login() -> None:
    """SSH analyzer identifies enabled root login."""
    analyzer = SshAnalyzer()
    findings = analyzer.analyze(Path("/etc/ssh/sshd_config"), "PermitRootLogin yes")

    assert findings[0].severity == "HIGH"
    assert "PermitRootLogin" in findings[0].reason


def test_cron_analyzer_marks_cron_changes_medium() -> None:
    """Cron analyzer returns medium severity for cron content."""
    analyzer = CronAnalyzer()
    findings = analyzer.analyze(Path("/etc/crontab"), "* * * * * root id")

    assert findings[0].severity == "MEDIUM"


def test_core_analyzer_engine_returns_standard_schema() -> None:
    """Core analyzer engine returns normalized security results."""
    engine = create_default_engine()

    results = engine.analyze(
        {
            "file_path": "/etc/ssh/sshd_config",
            "event_type": "modified",
            "details": "File /etc/ssh/sshd_config modified",
            "timestamp": "2026-06-23T21:10:00+00:00",
            "content": "PermitRootLogin yes\n",
        }
    )

    assert results == [
        {
            "file_path": "/etc/ssh/sshd_config",
            "severity": "HIGH",
            "reason": "PermitRootLogin is enabled",
            "recommendation": "Set PermitRootLogin to no or prohibit-password.",
        }
    ]
