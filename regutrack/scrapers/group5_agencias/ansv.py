"""ANSV — Agencia Nacional de Seguridad Vial scraper."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://ansv.gov.co"

class ANSVScraper(BaseScraper):
    entity_name = "Agencia Nacional de Seguridad Vial (ANSV)"
    entity_url = f"{_BASE}/es/normativa"
    entity_group = "group5_agencias"
    doc_type_default = "Resolución ANSV"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
