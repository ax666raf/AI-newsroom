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
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone as tz

from .runner import run_pipeline

logger = logging.getLogger(__name__)

# Algeria is UTC+1 (CET, no DST)
ALGERIA_TZ = tz("Africa/Algiers")

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    """
    Create and start the APScheduler background scheduler.
    Safe to call multiple times (idempotent).
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.info("Scheduler already running, skipping start")
        return

    _scheduler = BackgroundScheduler(timezone=ALGERIA_TZ)

    # Morning run — primary daily briefing
    _scheduler.add_job(
        run_pipeline,
        CronTrigger(hour=6, minute=0, timezone=ALGERIA_TZ),
        id="morning_run",
        name="Morning collection (06:00 DZ)",
        replace_existing=True,
    )

    # Midday top-up — catches breaking news
    _scheduler.add_job(
        run_pipeline,
        CronTrigger(hour=12, minute=0, timezone=ALGERIA_TZ),
        id="midday_run",
        name="Midday top-up (12:00 DZ)",
        replace_existing=True,
        kwargs={"top_up": True},
    )

    # Evening update
    _scheduler.add_job(
        run_pipeline,
        CronTrigger(hour=18, minute=0, timezone=ALGERIA_TZ),
        id="evening_run",
        name="Evening update (18:00 DZ)",
        replace_existing=True,
        kwargs={"top_up": True},
    )

    _scheduler.start()
    logger.info("Pipeline scheduler started (Algeria timezone, 3 daily runs)")


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler (called on app shutdown)."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Pipeline scheduler stopped")

