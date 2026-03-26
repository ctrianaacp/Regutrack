"""Imprenta Nacional (Diario Oficial) scraper."""

import re
from bs4 import BeautifulSoup

from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html


class ImprentaNacionalScraper(BaseScraper):
    entity_name = "Imprenta Nacional (Diario Oficial)"
    entity_url = "https://www.imprenta.gov.co/diario-oficial"
    entity_group = "group1_centralizadores"
    doc_type_default = "Diario Oficial"

    async def fetch_documents(self) -> list[DocumentResult]:
        docs = []
        url = "https://www.imprenta.gov.co/diario-oficial"
        try:
            html = await fetch_html(url)
        except Exception:
            # Fallback to homepage
            url = "https://www.imprenta.gov.co/"
            html = await fetch_html(url)

        soup = BeautifulSoup(html, "lxml")

        # Diario Oficial lists editions with links
        for link_el in soup.select("a[href]"):
            text = link_el.get_text(strip=True)
            href = link_el["href"]

            # Filter for "diario" or edition number patterns
            if not re.search(r"diario|edici[oó]n|\d{5}", text, re.IGNORECASE):
                continue
            if len(text) < 5:
                continue

            if not href.startswith("http"):
                href = "https://www.imprenta.gov.co" + href

            number = re.search(r"(\d{5,})", text)
            docs.append(
                DocumentResult(
                    title=text,
                    url=href,
                    doc_type="Diario Oficial",
                    number=number.group(1) if number else None,
                )
            )

        return docs[:50]
