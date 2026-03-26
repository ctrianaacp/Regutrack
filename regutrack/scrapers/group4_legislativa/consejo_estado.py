"""Consejo de Estado scraper."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.consejodeestado.gov.co"

class ConsejoEstadoScraper(BaseScraper):
    entity_name = "Consejo de Estado"
    entity_url = f"{_BASE}/relatoria/"
    entity_group = "group4_legislativa"
    doc_type_default = "Sentencia Consejo de Estado"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
