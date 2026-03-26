"""Superintendencia de Industria y Comercio (SIC) scraper.

The SIC has a dedicated search portal for administrative acts.
Targets: https://buscadoractos.sic.gov.co
"""
import re
from bs4 import BeautifulSoup

from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://buscadoractos.sic.gov.co"


class SICScraper(BaseScraper):
    entity_name = "Superintendencia de Industria y Comercio (SIC)"
    entity_url = "https://buscadoractos.sic.gov.co/#/"
    entity_group = "group3_control"
    doc_type_default = "Acto Administrativo SIC"
    requires_js = True  # Vue SPA with hash routing

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        """Use Playwright to interact with the SPA portal."""
        docs = []
        await page.goto("https://buscadoractos.sic.gov.co/#/", timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        for row in soup.select("table tr, .actList li, .resultado-busqueda"):
            link_el = row.select_one("a[href]")
            title = row.get_text(separator=" ", strip=True)
            if not title or len(title) < 5:
                continue
            href = link_el["href"] if link_el else ""
            if href and not href.startswith("http"):
                href = _BASE + href

            doc_type, number = _parse_type_number(title)
            docs.append(DocumentResult(
                title=title[:200],
                url=href or self.entity_url,
                doc_type=doc_type,
                number=number,
                raw_summary=title[:500],
            ))

        return docs[:80]


def _parse_type_number(title: str) -> tuple[str, str]:
    m = re.search(r"(Resolución|Circular|Auto|Acuerdo|Concepto)\s+([\d\-]+)", title, re.IGNORECASE)
    if m:
        return m.group(1).capitalize(), m.group(2)
    return "Acto Administrativo", ""
