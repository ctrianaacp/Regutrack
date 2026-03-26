"""Documents router — browse and filter regulatory documents."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Query
from regutrack.database import get_session
from regutrack.models import Document, Entity
from api.schemas import DocumentSchema, PaginatedDocuments

router = APIRouter(tags=["Documents"])


def _to_schema(session, doc: Document) -> DocumentSchema:
    entity = session.query(Entity).filter_by(id=doc.entity_id).first()
    return DocumentSchema(
        id=doc.id,
        entity_id=doc.entity_id,
        entity_name=entity.name if entity else None,
        title=doc.title,
        doc_type=doc.doc_type,
        number=doc.number,
        publication_date=doc.publication_date,
        url=doc.url,
        raw_summary=doc.raw_summary,
        is_new=doc.is_new,
        first_seen_at=doc.first_seen_at,
        last_seen_at=doc.last_seen_at,
    )


@router.get("/documents", response_model=PaginatedDocuments)
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_id: Optional[int] = None,
    doc_type: Optional[str] = None,
    is_new: Optional[bool] = None,
    search: Optional[str] = None,
    days: Optional[int] = None,
):
    """Paginated list of regulatory documents with optional filters."""
    with get_session() as session:
        query = session.query(Document)

        if entity_id:
            query = query.filter(Document.entity_id == entity_id)
        if doc_type:
            query = query.filter(Document.doc_type.ilike(f"%{doc_type}%"))
        if is_new is not None:
            query = query.filter(Document.is_new == is_new)
        if search:
            query = query.filter(
                Document.title.ilike(f"%{search}%")
                | Document.number.ilike(f"%{search}%")
            )
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Document.first_seen_at >= cutoff)

        total = query.count()
        items = (
            query.order_by(Document.first_seen_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return PaginatedDocuments(
            total=total,
            page=page,
            page_size=page_size,
            items=[_to_schema(session, d) for d in items],
        )


@router.get("/documents/new", response_model=list[DocumentSchema])
def get_new_documents(days: int = Query(7, ge=1, le=90)):
    """Get all documents found in the last N days (is_new=True)."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    with get_session() as session:
        docs = (
            session.query(Document)
            .filter(Document.first_seen_at >= cutoff)
            .order_by(Document.first_seen_at.desc())
            .limit(200)
            .all()
        )
        return [_to_schema(session, d) for d in docs]


@router.get("/documents/{doc_id}", response_model=DocumentSchema)
def get_document(doc_id: int):
    from fastapi import HTTPException
    with get_session() as session:
        doc = session.query(Document).filter_by(id=doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return _to_schema(session, doc)
