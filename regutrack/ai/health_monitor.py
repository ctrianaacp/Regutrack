"""HealthMonitor — Predictive DOM structure change detection.

Computes a structural fingerprint of a page (tag sequence, no content)
and stores it in the database. When the structure changes significantly,
it triggers an AI re-analysis BEFORE the scraper fails silently.

This is the PREDICTIVE component — it gives early warning that a site
has changed layout, so the system can proactively adapt.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from regutrack.models import DomFingerprint

logger = logging.getLogger(__name__)

# Minimum number of stable runs before we trust the fingerprint
_MIN_STABLE_RUNS = 3

# Tags that are layout-significant (we care if these change structure)
_LAYOUT_TAGS = {
    "div", "table", "tr", "td", "th", "ul", "ol", "li",
    "article", "section", "main", "nav", "header", "footer",
    "form", "select", "input", "a", "h1", "h2", "h3", "h4",
}


def _compute_structure_hash(html: str) -> str:
    """Hash the tag sequence (not content) of an HTML document.

    This is layout-sensitive: if the site changes from a <table> to a <ul>,
    or adds/removes major containers, the hash changes. Text changes don't matter.
    """
    soup = BeautifulSoup(html, "lxml")
    # Walk the tree, collect tag names only for layout tags
    tags = [
        tag.name
        for tag in soup.find_all(True)
        if tag.name in _LAYOUT_TAGS
    ]
    # Hash the sequence
    signature = "|".join(tags)
    return hashlib.sha256(signature.encode()).hexdigest()


class HealthMonitor:
    """Detect DOM structural changes for early warning of scraper degradation."""

    @staticmethod
    def check_and_update(
        session: Session,
        entity_id: int,
        html: str,
    ) -> tuple[bool, str]:
        """
        Check if the page structure has changed compared to the stored fingerprint.

        Returns:
            (changed: bool, message: str)
            changed=True means a significant structural change was detected.
        """
        current_hash = _compute_structure_hash(html)
        record = session.query(DomFingerprint).filter_by(entity_id=entity_id).first()

        if record is None:
            # First time — store baseline
            record = DomFingerprint(
                entity_id=entity_id,
                structure_hash=current_hash,
                stable_count=1,
                change_count=0,
                last_checked_at=datetime.utcnow(),
            )
            session.add(record)
            session.commit()
            logger.debug(f"[HealthMonitor] Baseline fingerprint stored for entity_id={entity_id}")
            return False, "baseline_stored"

        record.last_checked_at = datetime.utcnow()

        if current_hash == record.structure_hash:
            # Structure unchanged — increment stability counter
            record.stable_count += 1
            session.commit()
            return False, "stable"
        else:
            # Structure changed!
            record.change_count += 1
            record.last_changed_at = datetime.utcnow()

            msg = (
                f"DOM structure changed for entity_id={entity_id} "
                f"(change #{record.change_count}). "
                f"Old hash: {record.structure_hash[:8]}… → New: {current_hash[:8]}…"
            )
            logger.warning(f"[HealthMonitor] ⚠️ {msg}")

            # Update stored hash to the new structure
            record.structure_hash = current_hash
            record.stable_count = 1
            session.commit()

            return True, msg

    @staticmethod
    def is_count_degraded(
        session: Session,
        entity_id: int,
        current_doc_count: int,
        threshold_ratio: float = 0.3,
    ) -> bool:
        """
        Detect sudden drop in document count vs historical average.

        If the current run found < 30% of the average from previous runs,
        this signals the scraper may be silently broken.
        """
        from regutrack.models import ScrapeRun
        import statistics

        recent_runs = (
            session.query(ScrapeRun)
            .filter(
                ScrapeRun.entity_id == entity_id,
                ScrapeRun.status == "success",
                ScrapeRun.new_documents > 0,
            )
            .order_by(ScrapeRun.started_at.desc())
            .limit(10)
            .all()
        )

        if len(recent_runs) < 3:
            return False  # Not enough history to judge

        counts = [r.new_documents for r in recent_runs]
        avg = statistics.mean(counts)

        if avg < 1:
            return False

        ratio = current_doc_count / avg
        degraded = ratio < threshold_ratio

        if degraded:
            logger.warning(
                f"[HealthMonitor] ⚠️ Count degradation for entity_id={entity_id}: "
                f"{current_doc_count} docs vs avg {avg:.1f} (ratio={ratio:.2f})"
            )
        return degraded
