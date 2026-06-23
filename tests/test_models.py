"""Model smoke tests."""

from datetime import datetime, timezone

from configguardian.models.alert_model import AlertMessage
from configguardian.models.snapshot_model import Snapshot


def test_snapshot_model_accepts_required_fields() -> None:
    """Snapshot model stores core metadata."""
    now = datetime.now(tz=timezone.utc)
    snapshot = Snapshot(
        file_path="/etc/passwd",
        sha256="a" * 64,
        size_bytes=12,
        modified_at=now,
        content="root:x:0:0:root:/root:/bin/bash",
        created_at=now,
    )

    assert snapshot.file_path == "/etc/passwd"
    assert snapshot.size_bytes == 12


def test_alert_message_model_accepts_required_fields() -> None:
    """Alert messages expose provider-independent payload fields."""
    now = datetime.now(tz=timezone.utc)
    message = AlertMessage(
        severity="HIGH",
        file_path="/etc/ssh/sshd_config",
        reason="PermitRootLogin enabled",
        created_at=now,
    )

    assert message.severity == "HIGH"

