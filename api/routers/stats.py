"""Stats router — summary numbers for the dashboard."""

from datetime import datetime, timedelta
from fastapi import APIRouter
from regutrack.database import get_session
from regutrack.models import Entity, Document, ScrapeRun
from api.schemas import StatsSchema

router = APIRouter(tags=["Stats"])


@router.get("/stats", response_model=StatsSchema)
def get_stats():
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    with get_session() as session:
        total_entities = session.query(Entity).count()
        active_entities = session.query(Entity).filter_by(is_active=True).count()
        total_documents = session.query(Document).count()

        new_today = session.query(Document).filter(
            Document.first_seen_at >= today_start
        ).count()

        new_week = session.query(Document).filter(
            Document.first_seen_at >= week_start
        ).count()

        total_runs = session.query(ScrapeRun).count()

        runs_today = session.query(ScrapeRun).filter(
            ScrapeRun.started_at >= today_start
        ).all()
        successful_today = sum(1 for r in runs_today if r.status == "success")
        failed_today = sum(1 for r in runs_today if r.status == "failed")
        rate = (successful_today / len(runs_today)) if runs_today else 0.0

        last_run = session.query(ScrapeRun).order_by(
            ScrapeRun.started_at.desc()
        ).first()
        # Extract datetime value INSIDE the session to avoid DetachedInstanceError
        last_run_at = last_run.started_at if last_run else None

    return StatsSchema(
        total_entities=total_entities,
        active_entities=active_entities,
        total_documents=total_documents,
        new_documents_today=new_today,
        new_documents_week=new_week,
        total_runs=total_runs,
        successful_runs_today=successful_today,
        failed_runs_today=failed_today,
        success_rate_today=round(rate, 2),
        last_run_at=last_run_at,
    )
