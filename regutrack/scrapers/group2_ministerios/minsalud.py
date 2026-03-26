"""Ministerio de Salud scraper."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.minsalud.gov.co"

class MinsaludScraper(BaseScraper):
    entity_name = "Ministerio de Salud"
    entity_url = f"{_BASE}/Normatividad_Nuevo/Forms/AllItems.aspx"
    entity_group = "group2_ministerios"
    doc_type_default = "Norma Salud"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
