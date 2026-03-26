"""SelectorStore — Persists and loads AI-learned CSS selectors from the database.

When the LLM successfully extracts documents from a page, the discovered CSS selectors
are saved here. Future runs try the learned selectors first (fast, no API cost).
Only if they fail does the system fall back to the LLM again.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from regutrack.models import LearnedSelector
from regutrack.utils.hashing import DocumentResult

logger = logging.getLogger(__name__)


class SelectorStore:
    """Persist and apply AI-learned selectors for a given entity."""

    @staticmethod
    def save(
        session: Session,
        entity_id: int,
        selectors: dict[str, Any] | None,
        llm_strategy_json: dict | None = None,
        docs_found: int = 0,
    ) -> None:
        """Save or update learned selectors for an entity."""
        if not selectors:
            return

        record = session.query(LearnedSelector).filter_by(entity_id=entity_id).first()
        if record is None:
            record = LearnedSelector(entity_id=entity_id)
            session.add(record)

        record.list_selector = selectors.get("list_container")
        record.item_selector = selectors.get("item_row")
        record.title_selector = selectors.get("title_element")
        record.link_selector = selectors.get("link_element")
        record.date_selector = selectors.get("date_element")
        record.docs_found_last = docs_found
        record.success_count = (record.success_count or 0) + 1

        if llm_strategy_json:
            record.llm_strategy_json = json.dumps(llm_strategy_json, ensure_ascii=False)

        session.commit()
        logger.info(f"[SelectorStore] Saved selectors for entity_id={entity_id}")

    @staticmethod
    def load(session: Session, entity_id: int) -> LearnedSelector | None:
        """Load previously learned selectors for an entity. Returns None if not found."""
        return session.query(LearnedSelector).filter_by(entity_id=entity_id).first()

    @staticmethod
    def mark_failure(session: Session, entity_id: int) -> None:
        """Increment failure count for an entity's selectors."""
        record = session.query(LearnedSelector).filter_by(entity_id=entity_id).first()
        if record:
            record.failure_count = (record.failure_count or 0) + 1
            session.commit()

    @staticmethod
    def apply(
        html: str,
        entity_url: str,
        selector_record: LearnedSelector,
    ) -> list[DocumentResult]:
        """
        Apply learned CSS selectors to HTML and return extracted documents.
        Returns empty list if selectors fail or don't match.
        """
        if not selector_record or not selector_record.item_selector:
            return []

        try:
            soup = BeautifulSoup(html, "lxml")
            base = entity_url

            # Find all items
            item_sel = selector_record.item_selector
            items = soup.select(item_sel)
            if not items:
                logger.debug(f"[SelectorStore] item_selector '{item_sel}' matched 0 elements")
                return []

            docs: list[DocumentResult] = []
            seen: set[str] = set()

            for item in items:
                # Extract title
                title = ""
                if selector_record.title_selector:
                    el = item.select_one(selector_record.title_selector)
                    if el:
                        title = el.get_text(strip=True)
                if not title:
                    title = item.get_text(separator=" ", strip=True)[:300]

                # Extract URL
                url = None
                if selector_record.link_selector:
                    el = item.select_one(selector_record.link_selector)
                    if el and el.get("href"):
                        href = el["href"]
                        if not href.startswith("http"):
                            from urllib.parse import urljoin
                            href = urljoin(base, href)
                        url = href
                if not url:
                    a = item.select_one("a[href]")
                    if a:
                        href = a["href"]
                        if not href.startswith("http"):
                            from urllib.parse import urljoin
                            href = urljoin(base, href)
                        url = href

                if url and url in seen:
                    continue
                if url:
                    seen.add(url)

                # Try to parse type/number from title
                from regutrack.scrapers.common import parse_type_number, extract_date_from_text
                doc_type, number = parse_type_number(title)
                pub_date = extract_date_from_text(title)

                doc = DocumentResult(
                    title=title,
                    url=url or entity_url,
                    doc_type=doc_type,
                    number=number,
                    publication_date=pub_date,
                )
                if doc.is_valid():
                    docs.append(doc)

            logger.info(
                f"[SelectorStore] Applied selectors: {len(docs)} docs from {len(items)} items"
            )
            return docs

        except Exception as e:
            logger.warning(f"[SelectorStore] Failed to apply selectors: {e}")
            return []
