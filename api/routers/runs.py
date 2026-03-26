"""Scrape runs router — execution history."""

from typing import Optional
from fastapi import APIRouter, Query
from regutrack.database import get_session
from regutrack.models import ScrapeRun, Entity
from api.schemas import ScrapeRunSchema

router = APIRouter(tags=["Runs"])


def _to_schema(session, run: ScrapeRun) -> ScrapeRunSchema:
    entity = session.query(Entity).filter_by(id=run.entity_id).first()
    return ScrapeRunSchema(
        id=run.id,
        entity_id=run.entity_id,
        entity_name=entity.name if entity else None,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status,
        new_documents=run.new_documents,
        error_message=run.error_message,
    )


@router.get("/runs", response_model=list[ScrapeRunSchema])
def list_runs(
    entity_id: Optional[int] = None,
    status: Optional[str] = Query(None, pattern="^(success|failed|partial|running)$"),
    limit: int = Query(100, ge=1, le=500),
):
    """List recent scrape runs, optionally filtered by entity or status."""
    with get_session() as session:
        query = session.query(ScrapeRun)
        if entity_id:
            query = query.filter(ScrapeRun.entity_id == entity_id)
        if status:
            query = query.filter(ScrapeRun.status == status)
        runs = query.order_by(ScrapeRun.started_at.desc()).limit(limit).all()
        return [_to_schema(session, r) for r in runs]


@router.get("/runs/latest", response_model=list[ScrapeRunSchema])
def latest_runs_per_entity():
    """Return the most recent run for each entity (for status overview)."""
    with get_session() as session:
        # Get latest run per entity using subquery
        from sqlalchemy import func
        from sqlalchemy.orm import aliased

        subq = (
            session.query(
                ScrapeRun.entity_id,
                func.max(ScrapeRun.started_at).label("max_started")
            )
            .group_by(ScrapeRun.entity_id)
            .subquery()
        )
        runs = (
            session.query(ScrapeRun)
            .join(subq, (ScrapeRun.entity_id == subq.c.entity_id) &
                        (ScrapeRun.started_at == subq.c.max_started))
            .all()
        )
        return [_to_schema(session, r) for r in runs]
