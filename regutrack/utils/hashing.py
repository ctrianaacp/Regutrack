"""Utilities for content hashing and change detection."""

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class DocumentResult:
    """Data container returned by every scraper's fetch_documents() method."""

    title: str
    url: str
    doc_type: Optional[str] = None
    number: Optional[str] = None
    publication_date: Optional[date] = None
    raw_summary: Optional[str] = None

    def compute_hash(self) -> str:
        """
        Compute a stable SHA-256 fingerprint for change detection.
        Based on title + number + url so that metadata changes are caught
        but cosmetic whitespace differences are ignored.
        """
        raw = "|".join([
            (self.title or "").strip().lower(),
            (self.number or "").strip().lower(),
            (self.url or "").strip().lower(),
        ])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def is_valid(self) -> bool:
        """Return True if the document has at least a title."""
        return bool(self.title and self.title.strip())
