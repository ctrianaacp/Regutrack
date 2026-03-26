"""SUIN-Juriscol (MinJusticia) scraper — Sistema Único de Información Normativa."""

from bs4 import BeautifulSoup

from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html


class SuinJuriscolScraper(BaseScraper):
    entity_name = "SUIN-Juriscol (MinJusticia)"
    entity_url = "https://www.suin-juriscol.gov.co/legislacion/normatividad.html"
    entity_group = "group1_centralizadores"
    doc_type_default = "Norma"

    async def fetch_documents(self) -> list[DocumentResult]:
        docs = []
        # SUIN publishes recent norms via a search page; we target the "últimas normas" view
        url = "https://www.suin-juriscol.gov.co/legislacion/normatividad.html"
        html = await fetch_html(url)
        soup = BeautifulSoup(html, "lxml")

        # Look for table rows or list items with normative content
        for row in soup.select("table tr, ul.normativa li, .item-norm"):
            title_el = row.select_one("a, .titulo, td:first-child")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            link = title_el.get("href", "") if title_el.name == "a" else ""
            if link and not link.startswith("http"):
                link = "http://www.suin-juriscol.gov.co" + link

            # Try to extract doc type and number from title
            doc_type, number = _parse_type_number(title)

            docs.append(
                DocumentResult(
                    title=title,
                    url=link or url,
                    doc_type=doc_type,
                    number=number,
                )
            )

        return docs[:100]  # Cap to most recent 100


def _parse_type_number(title: str) -> tuple[str, str]:
    """Try to extract doc type and number from a norm title string."""
    import re
    patterns = [
        (r"(Ley|Decreto|Resolución|Circular|Acuerdo|Auto)\s+(\d+)", None),
        (r"(Sentencia)\s+([\w\-]+)", None),
    ]
    for pattern, _ in patterns:
        m = re.search(pattern, title, re.IGNORECASE)
        if m:
            return m.group(1).capitalize(), m.group(2)
    return "Norma", ""
