"""Procuraduría General de la Nación scraper."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.procuraduria.gov.co"

class ProcuradoriaScraper(BaseScraper):
    entity_name = "Procuraduría General de la Nación"
    entity_url = f"{_BASE}/portal/normatividad.page"
    entity_group = "group3_control"
    doc_type_default = "Directiva Procuraduría"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
