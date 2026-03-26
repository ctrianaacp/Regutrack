"""Tests for database initialization and ORM models."""

import os
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def in_memory_session():
    """Create an in-memory SQLite DB for testing."""
    # Override DB URL to use in-memory SQLite
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    from regutrack.models import Base
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_tables_created(in_memory_session):
    """All expected tables should be present after init."""
    from regutrack.models import Base
    engine = in_memory_session.bind
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "entities" in tables
    assert "documents" in tables
    assert "scrape_runs" in tables


def test_entity_crud(in_memory_session):
    """Create and read an entity."""
    from regutrack.models import Entity
    entity = Entity(
        name="Test Entity",
        group="test_group",
        url="https://test.gov.co",
        scraper_class="TestScraper",
        is_active=True,
    )
    in_memory_session.add(entity)
    in_memory_session.commit()

    result = in_memory_session.query(Entity).filter_by(name="Test Entity").first()
    assert result is not None
    assert result.group == "test_group"


def test_document_crud(in_memory_session):
    """Create a document linked to an entity."""
    from regutrack.models import Entity, Document
    from datetime import datetime

    entity = Entity(
        name="Test Entity",
        group="test",
        url="https://test.gov.co",
        scraper_class="TestScraper",
    )
    in_memory_session.add(entity)
    in_memory_session.flush()

    doc = Document(
        entity_id=entity.id,
        title="Resolución 1 de 2024",
        doc_type="Resolución",
        number="1",
        content_hash="a" * 64,
        is_new=True,
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
    )
    in_memory_session.add(doc)
    in_memory_session.commit()

    result = in_memory_session.query(Document).filter_by(number="1").first()
    assert result is not None
    assert result.doc_type == "Resolución"
