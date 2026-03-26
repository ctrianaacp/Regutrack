"""ANH — Agencia Nacional de Hidrocarburos scraper.

The ANH has a well-structured normatividad section.
URL: https://www.anh.gov.co/transparencia/normatividad/
"""
import re
from bs4 import BeautifulSoup
from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.anh.gov.co"
# Pre-filtered: type=10 (resoluciones), from 2020-01-01
_URL = f"{_BASE}/es/normatividad2/normatividad/?sector=&type=10&number=&keyword=&start_date=2020-01-01&end_date="


class ANHScraper(BaseScraper):
    entity_name = "Agencia Nacional de Hidrocarburos (ANH)"
    entity_url = _URL
    entity_group = "group5_agencias"
    doc_type_default = "Resolución ANH"

    async def fetch_documents(self) -> list[DocumentResult]:
        docs = []
        html = await fetch_html(_URL)
        soup = BeautifulSoup(html, "lxml")

        # ANH uses standard Gov Colombia template (Bootstrap table)
        for row in soup.select("table tr, .views-row, .item"):
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
            from regutrack.scrapers.common import extract_date_from_text
            pub_date = extract_date_from_text(title)

            docs.append(DocumentResult(
                title=title[:200],
                url=href or _URL,
                doc_type=doc_type,
                number=number,
                publication_date=pub_date,
                raw_summary=title[:400],
            ))

        seen = set()
        result = []
        for d in docs:
            key = d.url
            if key not in seen and d.is_valid():
                seen.add(key)
                result.append(d)
        return result[:100]


def _parse_type_number(title: str) -> tuple[str, str]:
    m = re.search(
        r"(Resolución|Acuerdo|Circular|Decreto|Contrato)\s+([\d\-]+)",
        title, re.IGNORECASE
    )
    if m:
        return m.group(1).capitalize(), m.group(2)
    return "Resolución ANH", ""
