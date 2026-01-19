from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.billing.logic import run_daily_billing
from app.config import settings


def setup_scheduler(scheduler: AsyncIOScheduler, billing_task, timezone: str | None = None) -> None:
    trigger = CronTrigger(
        hour=settings.billing_hour,
        minute=settings.billing_minute,
        timezone=timezone or settings.timezone,
    )
    scheduler.add_job(billing_task, trigger)
