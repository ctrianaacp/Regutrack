"""DIAN scraper — Dirección de Impuestos y Aduanas Nacionales."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.dian.gov.co"

class DIANScraper(BaseScraper):
    entity_name = "DIAN"
    entity_url = f"{_BASE}/normatividad/Paginas/normas.aspx"
    entity_group = "group3_control"
    doc_type_default = "Resolución DIAN"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
