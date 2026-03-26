"""Entities router."""

import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from regutrack.database import get_session
from regutrack.models import Entity, Document, ScrapeRun
from api.schemas import EntitySchema, TriggerRunResponse

router = APIRouter(tags=["Entities"])
logger = logging.getLogger(__name__)

# Reverse map: ScraperClassName -> entity_key (built once at import time)
def _build_class_to_key() -> dict[str, str]:
    from regutrack.scrapers import SCRAPERS_BY_KEY
    return {cls.__name__: key for key, cls in SCRAPERS_BY_KEY.items()}

_CLASS_TO_KEY: dict[str, str] = _build_class_to_key()


def _enrich_entity(session, entity: Entity) -> EntitySchema:
    """Attach computed fields to an entity."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    last_run = (
        session.query(ScrapeRun)
        .filter_by(entity_id=entity.id)
        .order_by(ScrapeRun.started_at.desc())
        .first()
    )
    total_docs = session.query(Document).filter_by(entity_id=entity.id).count()
    new_today = (
        session.query(Document)
        .filter(Document.entity_id == entity.id, Document.first_seen_at >= today_start)
        .count()
    )

    return EntitySchema(
        id=entity.id,
        key=_CLASS_TO_KEY.get(entity.scraper_class, entity.scraper_class),
        name=entity.name,
        group=entity.group,
        url=entity.url,
        scraper_class=entity.scraper_class,
        is_active=entity.is_active,
        created_at=entity.created_at,
        last_run_at=last_run.started_at if last_run else None,
        last_run_status=last_run.status if last_run else None,
        total_documents=total_docs,
        new_documents_today=new_today,
    )


@router.get("/entities", response_model=list[EntitySchema])
def list_entities():
    """List all monitored entities with their current status."""
    with get_session() as session:
        entities = session.query(Entity).order_by(Entity.group, Entity.name).all()
        return [_enrich_entity(session, e) for e in entities]


@router.get("/entities/{entity_id}", response_model=EntitySchema)
def get_entity(entity_id: int):
    """Get a single entity by ID."""
    with get_session() as session:
        entity = session.query(Entity).filter_by(id=entity_id).first()
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        return _enrich_entity(session, entity)


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


def _run_scraper_bg(entity_key: str):
    """Background task: run one scraper, then send email notification if new docs found.

    Uses a fresh event loop to avoid 'bound to different event loop' errors
    that occur when asyncio.run() is called from within FastAPI's thread pool
    (which already has an event loop set by uvicorn).
    """
    from regutrack.scrapers import SCRAPERS_BY_KEY
    from regutrack.notifier import notify_new_documents, notify_run_summary

    scraper_cls = SCRAPERS_BY_KEY.get(entity_key)
    if not scraper_cls:
        logger.warning(f"[API Trigger] Unknown entity key: {entity_key}")
        return

    scraper = scraper_cls()
    docs_by_entity: dict[str, list] = {}

    # Create a brand-new event loop for this background thread to avoid
    # conflicts with uvicorn's main event loop.
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
                    # Snapshot before session closes to avoid lazy-load errors
                    plain_docs = [_doc_snapshot(d) for d in new_docs]
                    notify_new_documents(plain_docs, scraper.entity_name)
                    if plain_docs:
                        docs_by_entity[scraper.entity_name] = plain_docs

        logger.info(
            f"[API Trigger] {entity_key}: status={result.status}, "
            f"new_docs={result.new_documents}"
        )
    except Exception as exc:
        logger.error(f"[API Trigger] Error running {entity_key}: {exc}", exc_info=True)
    finally:
        loop.close()

    # Send consolidated email if any new documents were found
    notify_run_summary(docs_by_entity)


@router.post("/run/{entity_key}", response_model=TriggerRunResponse)
def trigger_run(entity_key: str, background_tasks: BackgroundTasks):
    """Trigger a scrape for a specific entity (runs in background, sends email if new docs)."""
    from regutrack.scrapers import SCRAPERS_BY_KEY
    scraper_cls = SCRAPERS_BY_KEY.get(entity_key.lower())
    if not scraper_cls:
        raise HTTPException(
            status_code=404,
            detail=f"Entity key '{entity_key}' not found. Use GET /api/entities to list valid keys.",
        )
    background_tasks.add_task(_run_scraper_bg, entity_key.lower())
    return TriggerRunResponse(
        entity_key=entity_key,
        entity_name=scraper_cls.entity_name,
        message=f"Scrape started for '{scraper_cls.entity_name}' in background.",
    )
