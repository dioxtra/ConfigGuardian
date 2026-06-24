"""Tests for the scheduler service."""

from time import sleep

import pytest

from configguardian.core.scheduler import SchedulerService


@pytest.mark.parametrize("invalid_time", ["25:00", "9:00", "abc"])
def test_every_day_rejects_invalid_time_format(invalid_time: str) -> None:
    """Invalid time strings are rejected."""
    service = SchedulerService()

    with pytest.raises(ValueError, match="Expected HH:MM in 24-hour format"):
        service.every_day(lambda: None, invalid_time)


@pytest.mark.parametrize("valid_time", ["09:00", "23:59"])
def test_every_day_accepts_valid_time(valid_time: str) -> None:
    """Valid time strings are accepted."""
    service = SchedulerService()

    service.every_day(lambda: None, valid_time)


def test_start_stop_lifecycle() -> None:
    """Scheduler starts and stops cleanly."""
    service = SchedulerService()

    service.start()
    sleep(0.05)
    assert service.is_running is True

    service.stop()
    assert service.is_running is False


def test_start_is_idempotent() -> None:
    """Starting an already running scheduler is a no-op."""
    service = SchedulerService()

    service.start()
    sleep(0.05)
    first_thread = service._thread

    service.start()
    sleep(0.05)

    assert service.is_running is True
    assert service._thread is first_thread

    service.stop()
