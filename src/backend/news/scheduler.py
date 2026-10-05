"""Keep the announcements table fresh.

    python -m backend.news.scheduler

Weekdays 09:00-16:00 IST: every 5 minutes. All other times: every 30 minutes
(companies often file after hours). Each run re-fetches the last couple of
days and relies on idempotent upserts. Overlapping runs are skipped.
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.news import config
from backend.news.client import logger, setup_logging
from backend.news.ingest import run

JOB_DEFAULTS = {"max_instances": 1, "coalesce": True, "misfire_grace_time": 120}


def _ingest_job():
    try:
        run(days=config.SCHEDULED_LOOKBACK_DAYS)
    except Exception:
        logger.exception("Scheduled ingest failed")


def triggers():
    """(market-hours trigger, off-hours trigger) in IST."""
    start, end = config.MARKET_HOURS
    tz = config.TIMEZONE
    market = CronTrigger(
        day_of_week="mon-fri", hour=f"{start}-{end - 1}",
        minute=f"*/{config.MARKET_INTERVAL_MIN}", timezone=tz,
    )
    # Off-hours: weekday evenings/nights (16:00 onward, before 09:00) and all weekend.
    off_hours = [
        CronTrigger(day_of_week="mon-fri", hour=f"{end}-23,0-{start - 1}",
                    minute=f"*/{config.OFF_HOURS_INTERVAL_MIN}", timezone=tz),
        CronTrigger(day_of_week="sat,sun",
                    minute=f"*/{config.OFF_HOURS_INTERVAL_MIN}", timezone=tz),
    ]
    return market, off_hours


def build_scheduler():
    scheduler = BlockingScheduler(timezone=config.TIMEZONE, job_defaults=JOB_DEFAULTS)
    market, off_hours = triggers()
    # One job id per trigger; max_instances only applies per job, so all jobs
    # share a single-thread executor to avoid concurrent runs across triggers.
    scheduler.add_executor("threadpool", "single", max_workers=1)
    scheduler.add_job(_ingest_job, market, id="news_market", executor="single")
    for i, trig in enumerate(off_hours):
        scheduler.add_job(_ingest_job, trig, id=f"news_off_{i}", executor="single")
    return scheduler


def main():
    setup_logging()
    scheduler = build_scheduler()
    logger.info("News scheduler started (market every %dm, otherwise every %dm, IST).",
                config.MARKET_INTERVAL_MIN, config.OFF_HOURS_INTERVAL_MIN)
    _ingest_job()  # catch up immediately on start
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("News scheduler stopped.")


if __name__ == "__main__":
    main()
