"""ANT — Agencia Nacional de Tierras scraper."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.ant.gov.co"

class ANTScraper(BaseScraper):
    entity_name = "Agencia Nacional de Tierras (ANT)"
    entity_url = f"{_BASE}/transparencia-y-acceso-a-la-informacion-publica/normativa"
    entity_group = "group5_agencias"
    doc_type_default = "Resolución ANT"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
