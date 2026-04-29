"""Abstract base class for all entity scrapers."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from regutrack.models import Document, Entity, ScrapeRun
from regutrack.utils.hashing import DocumentResult

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    """Summary of a single scrape run."""

    entity_name: str
    status: str  # success / failed / partial
    new_documents: int = 0
    total_fetched: int = 0
    error_message: Optional[str] = None


class BaseScraper(ABC):
    """Abstract base class for all ReguTrack scrapers.

    Subclasses must:
      - Set class-level `entity_name`, `entity_url`, `entity_group`
      - Implement `fetch_documents()` returning list[DocumentResult]
    """

    entity_name: str = ""
    entity_url: str = ""
    entity_group: str = ""
    doc_type_default: str = "Norma"
    requires_js: bool = False  # Set to True to use Playwright

    async def fetch_documents(self) -> list[DocumentResult]:
        """Fetch current list of documents from the entity's website.
        Override this in each scraper subclass.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Orchestration — do not override unless necessary
    # ------------------------------------------------------------------

    async def run(self, session: Session) -> ScrapeResult:
        """Main entry: fetch → AI fallback if needed → persist → health check → return."""
        from regutrack.config import settings

        run_record = self._start_run(session)
        result = ScrapeResult(entity_name=self.entity_name, status="running")
        entity = self._get_or_create_entity(session)
        _raw_html: str | None = None  # Cache fetched HTML for health check

        try:
            docs: list[DocumentResult] = []

            # ── Step 1: Try AI-learned selectors (fast, no LLM cost) ──────
            if settings.ai_scraper_enabled and not self.requires_js:
                from regutrack.ai.selector_store import SelectorStore
                saved = SelectorStore.load(session, entity.id)
                if saved and saved.success_count >= 2 and saved.failure_count <= saved.success_count:
                    # Fetch HTML once and try saved selectors
                    from regutrack.utils.http_client import fetch_html
                    _raw_html = await fetch_html(self.entity_url)
                    docs = SelectorStore.apply(_raw_html, self.entity_url, saved)
                    if docs:
                        logger.info(
                            f"[{self.entity_name}] ⚡ Learned selectors: {len(docs)} docs (no LLM)"
                        )
                    else:
                        SelectorStore.mark_failure(session, entity.id)

            # ── Step 2: Primary scraper (if selectors didn't produce docs) ─
            if not docs:
                docs = await self._safe_fetch()

            result.total_fetched = len(docs)

            # ── Step 3: AI fallback — activate only when docs==0 ──────────
            if len(docs) == 0 and settings.ai_scraper_enabled and settings.openai_api_key and not self.requires_js:
                logger.warning(
                    f"[{self.entity_name}] 0 docs from primary scraper. Activating AI fallback."
                )
                from regutrack.ai.llm_extractor import LLMExtractor
                from regutrack.ai.selector_store import SelectorStore
                from regutrack.utils.http_client import fetch_html

                if _raw_html is None:
                    _raw_html = await fetch_html(self.entity_url)

                extractor = LLMExtractor(
                    api_key=settings.openai_api_key,
                    model=settings.ai_model,
                )
                ai_docs, ai_selectors = await extractor.extract(
                    html=_raw_html,
                    entity_name=self.entity_name,
                    entity_url=self.entity_url,
                    max_chars=settings.ai_max_html_chars,
                )

                if ai_docs:
                    docs = ai_docs
                    result.total_fetched = len(docs)
                    logger.info(
                        f"[{self.entity_name}] 🤖 AI extracted {len(docs)} docs via Gemini"
                    )
                    # Persist selectors for next run
                    SelectorStore.save(
                        session=session,
                        entity_id=entity.id,
                        selectors=ai_selectors,
                        docs_found=len(docs),
                    )
                else:
                    logger.warning(f"[{self.entity_name}] AI fallback also returned 0 docs.")

            result.new_documents = self._persist_documents(session, docs)
            result.status = "success"
            logger.info(
                f"[{self.entity_name}] ✓ {result.total_fetched} fetched, "
                f"{result.new_documents} new"
            )

            # ── Step 4: DOM health check (predictive, post-run) ───────────
            if (
                settings.ai_scraper_enabled
                and settings.ai_dom_fingerprint_enabled
                and _raw_html
            ):
                from regutrack.ai.health_monitor import HealthMonitor
                changed, msg = HealthMonitor.check_and_update(session, entity.id, _raw_html)
                if changed:
                    logger.warning(f"[HealthMonitor] Structure change: {msg}")

        except Exception as exc:
            result.status = "failed"
            result.error_message = str(exc)
            logger.error(f"[{self.entity_name}] ✗ {exc}")
        finally:
            self._finish_run(session, run_record, result)

        return result

    async def _safe_fetch(self) -> list[DocumentResult]:
        """Wrap fetch_documents with Playwright if required."""
        if self.requires_js:
            return await self._fetch_with_playwright()
        return await self.fetch_documents()

    async def _fetch_with_playwright(self) -> list[DocumentResult]:
        """Fetch using Playwright headless browser for JS-rendered pages."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="es-CO",
                ignore_https_errors=True,
            )
            page = await context.new_page()
            try:
                return await self.fetch_documents_with_page(page)
            finally:
                await browser.close()

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        """Override this method (instead of fetch_documents) for JS scrapers."""
        raise NotImplementedError(
            f"{self.__class__.__name__} sets requires_js=True but does not "
            "implement fetch_documents_with_page()"
        )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _get_or_create_entity(self, session: Session) -> Entity:
        entity = session.query(Entity).filter_by(name=self.entity_name).first()
        if not entity:
            entity = Entity(
                name=self.entity_name,
                group=self.entity_group,
                url=self.entity_url,
                scraper_class=self.__class__.__name__,
                is_active=True,
            )
            session.add(entity)
            session.flush()
        return entity

    def _start_run(self, session: Session) -> ScrapeRun:
        entity = self._get_or_create_entity(session)
        run = ScrapeRun(entity_id=entity.id, started_at=datetime.utcnow(), status="running")
        session.add(run)
        session.flush()
        return run

    def _finish_run(self, session: Session, run: ScrapeRun, result: ScrapeResult) -> None:
        run.finished_at = datetime.utcnow()
        run.status = result.status
        run.new_documents = result.new_documents
        run.error_message = result.error_message
        session.flush()

    def _persist_documents(self, session: Session, docs: list[DocumentResult]) -> int:
        """
        Upsert documents into the DB using content_hash for deduplication.
        Returns the count of genuinely NEW documents.
        """
        entity = self._get_or_create_entity(session)
        now = datetime.utcnow()
        new_count = 0

        for doc in docs:
            if not doc.is_valid():
                continue

            h = doc.compute_hash()
            existing = (
                session.query(Document)
                .filter_by(entity_id=entity.id, content_hash=h)
                .first()
            )

            if existing:
                # Update last_seen timestamp; mark as not new
                existing.last_seen_at = now
                existing.is_new = False
            else:
                # New document!
                new_doc = Document(
                    entity_id=entity.id,
                    title=doc.title,
                    doc_type=doc.doc_type or self.doc_type_default,
                    number=doc.number,
                    publication_date=doc.publication_date,
                    url=doc.url,
                    raw_summary=doc.raw_summary,
                    content_hash=h,
                    is_new=True,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(new_doc)
                new_count += 1

        session.flush()
        return new_count
