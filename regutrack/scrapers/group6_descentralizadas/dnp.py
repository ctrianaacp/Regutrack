"""DNP — Departamento Nacional de Planeación scraper."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.dnp.gov.co"

class DNPScraper(BaseScraper):
    entity_name = "DNP (Planeación Nacional)"
    entity_url = f"{_BASE}/normativa/normograma"
    entity_group = "group6_descentralizadas"
    doc_type_default = "Decreto/CONPES DNP"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
