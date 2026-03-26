"""Aeronáutica Civil scraper — Reglamentos Aeronáuticos (RAC)."""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.aerocivil.gov.co"

class AerocivilScraper(BaseScraper):
    entity_name = "Aeronáutica Civil"
    entity_url = f"{_BASE}/normatividad/normas-aeron-uticas"
    entity_group = "group6_descentralizadas"
    doc_type_default = "Reglamento Aeronáutico (RAC)"

    async def fetch_documents(self) -> list[DocumentResult]:
        html = await fetch_html(self.entity_url)
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
