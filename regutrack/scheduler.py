"""APScheduler-based job runner — executes every N hours (default: 6)."""

import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pytz

from regutrack.config import settings

logger = logging.getLogger(__name__)


def _run_one_scraper(scraper_cls) -> tuple:
    """Run a single scraper in an isolated event loop (safe for Playwright).

    Each call creates its own event loop so Playwright's internal locks are
    never shared across scrapers — the root cause of the
    'bound to a different event loop' errors seen in concurrent runs.

    Returns a (result, entity_name, plain_docs) tuple.
    """
    from regutrack.database import get_session
    from regutrack.models import Document, Entity

    scraper = scraper_cls()
    plain_docs = []

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        with get_session() as session:
            result = loop.run_until_complete(scraper.run(session))

            if result.new_documents > 0:
                entity = session.query(Entity).filter_by(name=scraper.entity_name).first()
                if entity:
                    new_docs = (
                        session.query(Document)
                        .filter_by(entity_id=entity.id, is_new=True)
                        .all()
                    )
                    plain_docs = [_doc_snapshot(d) for d in new_docs]
    except Exception as exc:
        logger.error(
            f"[Scheduler] Error running {scraper_cls.__name__}: {exc}", exc_info=True
        )
        result = None
    finally:
        loop.close()

    return result, scraper.entity_name, plain_docs


def _run_all_sync() -> None:
    """Run every scraper sequentially, each in its own isolated event loop.

    Sequential execution is intentional: Playwright shares browser resources
    inside the same process, and concurrent launches cause lock conflicts.
    """
    from regutrack.scrapers import ALL_SCRAPERS
    from regutrack.notifier import notify_new_documents, notify_run_summary

    logger.info(f"[Scheduler] Starting scheduled run at {datetime.utcnow().isoformat()}Z")

    results = []
    docs_by_entity: dict[str, list] = {}

    for scraper_cls in ALL_SCRAPERS:
        result, entity_name, plain_docs = _run_one_scraper(scraper_cls)
        if result is not None:
            results.append(result)
            if plain_docs:
                notify_new_documents(plain_docs, entity_name)
                docs_by_entity[entity_name] = plain_docs

    total_new = sum(r.new_documents for r in results)
    total_ok  = sum(1 for r in results if r.status == "success")
    logger.info(
        f"[Scheduler] Run summary: {total_ok}/{len(results)} entities OK, "
        f"{total_new} new documents total"
    )

    # Send ONE consolidated email for the full run
    notify_run_summary(docs_by_entity)
    logger.info(f"[Scheduler] Scheduled run complete at {datetime.utcnow().isoformat()}Z")


def _doc_snapshot(doc):
    """Copy ORM Document fields to a plain object safe to use after session closes."""
    class _Snap:
        pass
    s = _Snap()
    s.title            = doc.title
    s.url              = doc.url
    s.doc_type         = doc.doc_type
    s.number           = doc.number
    s.publication_date = doc.publication_date
    s.raw_summary      = doc.raw_summary
    return s





def create_scheduler() -> BackgroundScheduler:
    """Create and configure the APScheduler instance.

    Runs every SCHEDULER_INTERVAL_HOURS hours, starting at the next occurrence
    of SCHEDULER_HOUR:SCHEDULER_MINUTE (America/Bogota).
    """
    bogota_tz = pytz.timezone("America/Bogota")
    scheduler = BackgroundScheduler(timezone=bogota_tz)

    interval_hours = settings.scheduler_interval_hours
    now = datetime.now(bogota_tz)

    # Compute the next start aligned to the configured clock time
    start = bogota_tz.localize(datetime(
        now.year, now.month, now.day,
        settings.scheduler_hour, settings.scheduler_minute, 0
    ))
    while start <= now:
        start += timedelta(hours=interval_hours)

    scheduler.add_job(
        _run_all_sync,
        trigger=IntervalTrigger(
            hours=interval_hours,
            start_date=start,
            timezone=bogota_tz,
        ),
        id="scrape_interval",
        name=f"ReguTrack Scrape Every {interval_hours}h",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    logger.info(
        f"[Scheduler] Configured to run every {interval_hours}h "
        f"(America/Bogota). First run: {start.strftime('%Y-%m-%d %H:%M %Z')}"
    )
    return scheduler
