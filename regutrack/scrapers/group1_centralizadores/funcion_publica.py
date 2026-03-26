"""Función Pública — Gestor Normativo scraper."""

import re
from bs4 import BeautifulSoup

from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html


class FuncionPublicaScraper(BaseScraper):
    entity_name = "Gestor Normativo (Función Pública)"
    entity_url = "https://www.funcionpublica.gov.co/eva/gestornormativo/"
    entity_group = "group1_centralizadores"
    doc_type_default = "Norma Función Pública"

    # Gestor Normativo search: returns recent norms
    _LISTING_URL = "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=1"

    async def fetch_documents(self) -> list[DocumentResult]:
        docs = []
        html = await fetch_html(self._LISTING_URL)
        soup = BeautifulSoup(html, "lxml")

        for row in soup.select("table tr"):
            cells = row.select("td")
            if len(cells) < 2:
                continue
            title_cell = cells[0]
            link_el = title_cell.select_one("a")
            title = title_cell.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            href = ""
            if link_el:
                href = link_el.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.funcionpublica.gov.co/eva/gestornormativo/" + href

            date_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            pub_date = _parse_date(date_text)

            doc_type, number = _parse_type_number(title)

            docs.append(
                DocumentResult(
                    title=title,
                    url=href or self._LISTING_URL,
                    doc_type=doc_type,
                    number=number,
                    publication_date=pub_date,
                )
            )

        return docs[:100]


def _parse_date(text: str):
    from datetime import date
    import re
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return None


def _parse_type_number(title: str) -> tuple[str, str]:
    import re
    m = re.search(r"(Ley|Decreto|Resolución|Circular|Acuerdo|Directiva)\s+(\d+)", title, re.IGNORECASE)
    if m:
        return m.group(1).capitalize(), m.group(2)
    return "Norma", ""
