"""Pydantic response schemas for the ReguTrack API."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class EntitySchema(BaseModel):
    id: int
    key: str                    # Exact key used in SCRAPERS_BY_KEY / POST /api/run/{key}
    name: str
    group: str
    url: str
    scraper_class: str
    is_active: bool
    created_at: datetime
    # Computed from latest ScrapeRun
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    total_documents: int = 0
    new_documents_today: int = 0

    class Config:
        from_attributes = True


class DocumentSchema(BaseModel):
    id: int
    entity_id: int
    entity_name: Optional[str] = None
    title: str
    doc_type: Optional[str] = None
    number: Optional[str] = None
    publication_date: Optional[date] = None
    url: Optional[str] = None
    raw_summary: Optional[str] = None
    is_new: bool
    first_seen_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True


class ScrapeRunSchema(BaseModel):
    id: int
    entity_id: int
    entity_name: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    new_documents: int
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class StatsSchema(BaseModel):
    total_entities: int
    active_entities: int
    total_documents: int
    new_documents_today: int
    new_documents_week: int
    total_runs: int
    successful_runs_today: int
    failed_runs_today: int
    success_rate_today: float  # 0.0 - 1.0
    last_run_at: Optional[datetime] = None


class PaginatedDocuments(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[DocumentSchema]


class TriggerRunResponse(BaseModel):
    entity_key: str
    entity_name: str
    message: str
