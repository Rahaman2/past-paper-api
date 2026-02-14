import time
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from scraper import get_exam_sessions, scrape_papers_from_url, group_papers_by_subject
from cache import save_cache_to_disk, get_cache

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_full_scrape() -> dict:
    """
    Scrape all sessions and all papers. Returns the full cache dict.
    On failure for individual sessions, logs and continues with others.
    """
    start = time.time()
    logger.info("Starting full scrape...")

    sessions = get_exam_sessions()
    logger.info("Found %d sessions", len(sessions))

    papers = {}
    errors = []

    for s in sessions:
        year = s.get("year")
        session_name = s.get("session")
        url = s.get("working_url")

        if not year or not session_name or not url:
            continue

        key = f"{year}|{session_name}"
        try:
            raw_papers = scrape_papers_from_url(url)
            grouped = group_papers_by_subject(raw_papers)
            papers[key] = grouped
            logger.info("Scraped %s: %d subjects", key, len(grouped))
        except Exception as e:
            logger.error("Failed to scrape %s: %s", key, e)
            errors.append({"session": key, "error": str(e)})
            # Preserve stale data for this session if available
            old_cache = get_cache()
            if old_cache and key in old_cache.get("papers", {}):
                papers[key] = old_cache["papers"][key]
                logger.info("Preserved stale data for %s", key)

    duration = time.time() - start

    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "scrape_duration_seconds": round(duration, 2),
        "scrape_errors": errors,
        "sessions": sessions,
        "papers": papers,
    }

    save_cache_to_disk(data)
    logger.info(
        "Full scrape completed in %.1fs. %d sessions, %d errors.",
        duration, len(papers), len(errors),
    )
    return data


def start_scheduler():
    """Start the background scheduler. Runs daily at 3 AM UTC (5 AM SAST)."""
    scheduler.add_job(
        run_full_scrape,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily_scrape",
        name="Daily paper scrape",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info("Scheduler started. Daily scrape at 03:00 UTC.")


def stop_scheduler():
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
