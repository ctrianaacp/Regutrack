"""Senado de la República scraper — Leyes y proyectos de ley."""
import re
from bs4 import BeautifulSoup
from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.senado.gov.co"

class SenadoScraper(BaseScraper):
    entity_name = "Senado de la República"
    entity_url = f"{_BASE}/"
    entity_group = "group4_legislativa"
    doc_type_default = "Ley"

    async def fetch_documents(self) -> list[DocumentResult]:
        docs = []
        # Try current leyes index page
        url = f"{_BASE}/legislacion/leyes.html"
        try:
            html = await fetch_html(url)
        except Exception:
            url = f"{_BASE}/"
            html = await fetch_html(url)
        soup = BeautifulSoup(html, "lxml")

        for link_el in soup.select("a[href]"):
            text = link_el.get_text(strip=True)
            href = link_el["href"]
            if not re.search(r"ley|proyecto|acto\s+legislativo", text, re.IGNORECASE):
                continue
            if len(text) < 5:
                continue
            if not href.startswith("http"):
                href = _BASE + href
            number_m = re.search(r"(\d+)\s+de\s+(\d{4})", text, re.IGNORECASE)
            docs.append(DocumentResult(
                title=text[:200],
                url=href,
                doc_type="Ley",
                number=number_m.group(0) if number_m else None,
            ))

        return docs[:80]
