"""Scheduled task orchestration."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from threading import Event, Thread
from typing import Final

import schedule

from configguardian.utils.logger import get_logger

_TIME_FORMAT: Final[str] = "%H:%M"


class SchedulerService:
    """Register and run recurring ConfigGuardian jobs."""

    def __init__(self) -> None:
        """Initialize the scheduler without starting the worker thread."""
        self.logger = get_logger(__name__)
        self._scheduler = schedule.Scheduler()
        self._stop_event = Event()
        self._thread: Thread | None = None

    def every_day(self, task: Callable[[], None], at_time: str) -> None:
        """Schedule a daily task at a validated 24-hour HH:MM time."""
        self._validate_time(at_time)
        self._scheduler.every().day.at(at_time).do(task)

    def start(self) -> None:
        """Start the background scheduler loop."""
        if self.is_running:
            self.logger.warning("SchedulerService is already running.")
            return

        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="configguardian-scheduler")
        self._thread.daemon = True
        self._thread.start()

    def stop(self) -> None:
        """Stop the background scheduler loop."""
        if not self.is_running:
            return

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            if not self._thread.is_alive():
                self._thread = None

    @property
    def is_running(self) -> bool:
        """Return whether the background scheduler thread is active."""
        return self._thread is not None and self._thread.is_alive()

    def _run_loop(self) -> None:
        """Continuously run pending jobs until stopped."""
        try:
            while not self._stop_event.is_set():
                self._scheduler.run_pending()
                self._stop_event.wait(1)
        finally:
            self._stop_event.clear()

    @staticmethod
    def _validate_time(at_time: str) -> None:
        """Validate a daily schedule time in HH:MM format."""
        try:
            parsed = datetime.strptime(at_time, _TIME_FORMAT)
        except ValueError as exc:
            raise ValueError(
                f"Invalid at_time '{at_time}'. Expected HH:MM in 24-hour format."
            ) from exc

        if parsed.strftime(_TIME_FORMAT) != at_time:
            raise ValueError(
                f"Invalid at_time '{at_time}'. Expected HH:MM in 24-hour format."
            )
