"""Corte Constitucional scraper — Sentencias T, C, SU."""
import re
from bs4 import BeautifulSoup
from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.corteconstitucional.gov.co"

class CorteConstitucionalScraper(BaseScraper):
    entity_name = "Corte Constitucional"
    entity_url = f"{_BASE}/relatoria/"
    entity_group = "group4_legislativa"
    doc_type_default = "Sentencia"

    async def fetch_documents(self) -> list[DocumentResult]:
        docs = []
        html = await fetch_html(self.entity_url)
        soup = BeautifulSoup(html, "lxml")

        for link_el in soup.select("a[href]"):
            text = link_el.get_text(strip=True)
            href = link_el["href"]
            # Sentencias have patterns like C-123-24, T-456-23, SU-789-22
            if not re.search(r"\b[CTSU]{1,2}-\d+[-/]\d{2,4}\b", text, re.IGNORECASE):
                continue
            if not href.startswith("http"):
                href = _BASE + href
            number_m = re.search(r"([CTSU]{1,2}-\d+[-/]\d{2,4})", text, re.IGNORECASE)
            docs.append(DocumentResult(
                title=text[:200],
                url=href,
                doc_type="Sentencia",
                number=number_m.group(1) if number_m else None,
            ))

        return docs[:80]
