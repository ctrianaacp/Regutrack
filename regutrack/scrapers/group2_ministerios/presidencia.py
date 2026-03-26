"""Presidencia de la República scraper."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://dapre.presidencia.gov.co"

class PresidenciaScraper(BaseScraper):
    entity_name = "Presidencia de la República"
    entity_url = f"{_BASE}/normativa/normativa"
    entity_group = "group2_ministerios"
    doc_type_default = "Decreto Presidencial"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
