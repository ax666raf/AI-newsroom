"""
scheduler.py — Background scheduler for the collection pipeline.

Runs the pipeline automatically at configured times every day.
Uses APScheduler (Advanced Python Scheduler) with a background
thread so it does not block the FastAPI process.

Schedule (configurable via settings):
  06:00  — Morning full run
  12:00  — Midday top-up
  18:00  — Evening update
"""

import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone as tz

from .runner import run_pipeline

logger = logging.getLogger(__name__)

# Algeria is UTC+1 (CET, no DST)
ALGERIA_TZ = tz("Africa/Algiers")

_scheduler: BackgroundScheduler | None = None
_scheduler_lock = threading.Lock()


def start_scheduler() -> None:
    """
    Create and start the APScheduler background scheduler.
    Safe to call multiple times (idempotent).
    """
    global _scheduler

    with _scheduler_lock:
        if _scheduler and _scheduler.running:
            logger.info("Scheduler already running, skipping start")
            return

        _scheduler = BackgroundScheduler(timezone=ALGERIA_TZ)

        # Primary daily run requested at 5 AM
        _scheduler.add_job(
            run_pipeline,
            CronTrigger(hour=5, minute=0, timezone=ALGERIA_TZ),
            id="morning_run",
            name="Morning collection (05:00 DZ)",
            replace_existing=True,
        )

        _scheduler.start()
        logger.info("Pipeline scheduler started (Algeria timezone, 1 daily run at 5 AM)")


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler (called on app shutdown)."""
    global _scheduler
    with _scheduler_lock:
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
            logger.info("Pipeline scheduler stopped")
        _scheduler = None

