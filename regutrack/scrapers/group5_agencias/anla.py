"""ANLA — Agencia Nacional de Licencias Ambientales scraper."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.anla.gov.co"

class ANLAScraper(BaseScraper):
    entity_name = "Autoridad Nacional de Licencias Ambientales (ANLA)"
    entity_url = "https://gaceta.anla.gov.co:8443/Consultar-gaceta"
    entity_group = "group5_agencias"
    doc_type_default = "Resolución ANLA"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
