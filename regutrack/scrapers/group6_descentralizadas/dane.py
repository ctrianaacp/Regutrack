"""DANE — Departamento Administrativo Nacional de Estadística scraper."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.dane.gov.co"

class DANEScraper(BaseScraper):
    entity_name = "DANE"
    entity_url = f"{_BASE}/index.php/acerca-del-dane/informacion-institucional/normatividad"
    entity_group = "group6_descentralizadas"
    doc_type_default = "Resolución DANE"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
