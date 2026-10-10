"""
APScheduler standalone runner for attendance monitoring.

Runs as an independent process/service from FastAPI web workers to avoid
duplicate job executions and resource contention.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import sys
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database.connection import close_database_connection, connect_to_database, get_database
from app.logging_config import setup_logging
from app.workers.monitoring import run_monitoring_cycle

logger = logging.getLogger("app.workers.scheduler")


async def scheduled_monitoring_job() -> None:
    """Execute scheduled attendance monitoring cycle."""
    logger.info("Starting scheduled attendance monitoring job...")
    try:
        db = get_database()
        summary = await run_monitoring_cycle(db)
        logger.info(
            "Monitoring job completed successfully: %s",
            summary,
        )
    except Exception as exc:
        logger.exception("Scheduled monitoring job failed: %s", exc)


async def main() -> None:
    """Entry point for standalone scheduler process."""
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info(
        "Initializing scheduler service (timezone=%s, cron=%s)...",
        settings.scheduler_timezone,
        settings.scheduler_cron,
    )

    await connect_to_database()

    scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
    trigger = CronTrigger.from_crontab(
        settings.scheduler_cron,
        timezone=settings.scheduler_timezone,
    )

    scheduler.add_job(
        scheduled_monitoring_job,
        trigger=trigger,
        id="attendance_monitoring_daily",
        name="Daily Attendance Compliance Monitoring",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    logger.info(
        "Scheduler started successfully. Next run time: %s",
        scheduler.get_jobs()[0].next_run_time if scheduler.get_jobs() else "N/A",
    )

    stop_event = asyncio.Event()

    def _shutdown_handler(*_: Any) -> None:
        logger.info("Received termination signal, shutting down scheduler...")
        stop_event.set()

    # Register signal handlers if supported (Windows supports SIGINT and SIGBREAK)
    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _shutdown_handler)
    else:
        # On Windows, register console signal handlers or catch KeyboardInterrupt
        try:
            signal.signal(signal.SIGINT, lambda *_: _shutdown_handler())
            signal.signal(signal.SIGTERM, lambda *_: _shutdown_handler())
        except Exception:
            pass

    try:
        await stop_event.wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Interrupted, shutting down...")
    finally:
        logger.info("Stopping scheduler...")
        scheduler.shutdown(wait=False)
        await close_database_connection()
        logger.info("Scheduler process exited.")


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt, SystemExit):
        asyncio.run(main())
