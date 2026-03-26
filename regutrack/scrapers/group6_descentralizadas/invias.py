"""INVÍAS scraper — Instituto Nacional de Vías."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.invias.gov.co"

class InviasScraper(BaseScraper):
    entity_name = "INVÍAS"
    entity_url = f"{_BASE}/normatividad"
    entity_group = "group6_descentralizadas"
    doc_type_default = "Resolución INVÍAS"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
