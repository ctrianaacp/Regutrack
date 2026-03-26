"""Secretaría Jurídica Distrital de Bogotá (Régimen Legal) scraper."""

import re
from bs4 import BeautifulSoup

from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.alcaldiabogota.gov.co"


class SecretariaJuridicaScraper(BaseScraper):
    entity_name = "Secretaría Jurídica Distrital de Bogotá"
    entity_url = f"{_BASE}/sisjur/"
    entity_group = "group1_centralizadores"
    doc_type_default = "Acto Administrativo Distrital"

    async def fetch_documents(self) -> list[DocumentResult]:
        docs = []
        # Main listing of recent norms
        url = f"{_BASE}/sisjur/normas/listadoNormas.jsp"
        try:
            html = await fetch_html(url)
        except Exception:
            url = f"{_BASE}/sisjur/"
            html = await fetch_html(url)
        soup = BeautifulSoup(html, "lxml")

        for row in soup.select("table tr"):
            cells = row.select("td")
            if len(cells) < 1:
                continue
            link_el = row.select_one("a[href]")
            title = row.get_text(separator=" ", strip=True)
            if not title or len(title) < 5:
                continue

            href = ""
            if link_el:
                href = link_el["href"]
                if not href.startswith("http"):
                    href = _BASE + href

            doc_type, number = _parse_type_number(title)
            docs.append(
                DocumentResult(
                    title=title[:200],
                    url=href or url,
                    doc_type=doc_type,
                    number=number,
                )
            )

        # Deduplicate by URL
        seen = set()
        result = []
        for d in docs:
            if d.url not in seen:
                seen.add(d.url)
                result.append(d)
        return result[:80]


def _parse_type_number(title: str) -> tuple[str, str]:
    m = re.search(r"(Decreto|Resolución|Circular|Acuerdo|Directiva)\s+(\d+)", title, re.IGNORECASE)
    if m:
        return m.group(1).capitalize(), m.group(2)
    return "Acto Administrativo", ""
