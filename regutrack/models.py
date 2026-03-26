"""SQLAlchemy ORM models for ReguTrack."""

from datetime import datetime, date
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Entity(Base):
    """A government entity whose normative publications are monitored."""

    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    group = Column(String(50), nullable=False)  # e.g. "group1_centralizadores"
    url = Column(String(500), nullable=False)
    scraper_class = Column(String(100), nullable=False)  # e.g. "ANHScraper"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="entity", cascade="all, delete-orphan")
    scrape_runs = relationship("ScrapeRun", back_populates="entity", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Entity id={self.id} name={self.name!r}>"


class Document(Base):
    """A regulatory document found during scraping."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("entity_id", "content_hash", name="uq_entity_hash"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)

    # Document metadata
    title = Column(Text, nullable=False)
    doc_type = Column(String(100), nullable=True)  # Ley, Decreto, Resolución, Circular, Sentencia
    number = Column(String(100), nullable=True)    # Number/ID of the document
    publication_date = Column(Date, nullable=True)
    url = Column(Text, nullable=True)
    raw_summary = Column(Text, nullable=True)      # First extracted text/description

    # Change detection
    content_hash = Column(String(64), nullable=False)  # SHA-256

    # Tracking
    is_new = Column(Boolean, default=True, nullable=False)  # New in the latest run?
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    entity = relationship("Entity", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document id={self.id} type={self.doc_type!r} number={self.number!r}>"


class ScrapeRun(Base):
    """A record of a scraping job execution for an entity."""

    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="running")  # running/success/failed/partial
    new_documents = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationship
    entity = relationship("Entity", back_populates="scrape_runs")

    def __repr__(self) -> str:
        return f"<ScrapeRun id={self.id} entity_id={self.entity_id} status={self.status!r}>"


class LearnedSelector(Base):
    """CSS/XPath selectors discovered by the AI extractor for a given entity.

    When the AI successfully extracts documents from a previously broken scraper,
    it persists the discovered selectors here so future runs skip the LLM call.
    """

    __tablename__ = "learned_selectors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, unique=True)

    # What the AI found
    list_selector = Column(Text, nullable=True)    # CSS selector for the doc list container
    item_selector = Column(Text, nullable=True)    # CSS selector for each item row
    title_selector = Column(Text, nullable=True)   # CSS selector for the title within each item
    link_selector = Column(Text, nullable=True)    # CSS selector for the link within each item
    date_selector = Column(Text, nullable=True)    # CSS selector for the date within each item

    # Quality tracking
    success_count = Column(Integer, default=0, nullable=False)   # How many runs used this successfully
    failure_count = Column(Integer, default=0, nullable=False)   # How many times it failed
    docs_found_last = Column(Integer, default=0, nullable=False) # Docs found in last successful run

    # The raw JSON strategy the LLM produced (fallback/debug)
    llm_strategy_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<LearnedSelector entity_id={self.entity_id} success={self.success_count}>"


class DomFingerprint(Base):
    """Structural fingerprint of a page's DOM — used to detect layout changes before
    the scraper breaks. Compares tag-sequence hashes, not content.
    """

    __tablename__ = "dom_fingerprints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, unique=True)

    # Structural hash (tags only, no text content)
    structure_hash = Column(String(64), nullable=False)

    # How many times we've seen this same structure
    stable_count = Column(Integer, default=1, nullable=False)

    # Counts of detected changes
    change_count = Column(Integer, default=0, nullable=False)

    last_checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_changed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<DomFingerprint entity_id={self.entity_id} hash={self.structure_hash[:8]}>"

