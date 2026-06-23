"""Scheduled task orchestration."""

from collections.abc import Callable

import schedule


class SchedulerService:
    """Register and run recurring ConfigGuardian jobs."""

    def every_day(self, task: Callable[[], None], at_time: str) -> None:
        """Schedule a daily task."""
        # TODO: Validate time format and expose lifecycle controls.
        schedule.every().day.at(at_time).do(task)

    def run_pending(self) -> None:
        """Run pending scheduled jobs."""
        schedule.run_pending()

