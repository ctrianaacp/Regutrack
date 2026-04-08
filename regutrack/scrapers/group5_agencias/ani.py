"""ANI — Agencia Nacional de Infraestructura scraper."""
from datetime import datetime
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.ani.gov.co"

class ANIScraper(BaseScraper):
    entity_name = "Agencia Nacional de Infraestructura (ANI)"
    entity_group = "group5_agencias"
    doc_type_default = "Norma ANI"

    @property
    def entity_url(self) -> str:
        """Dynamic URL fetching current year's documents to prevent aging."""
        current_year = datetime.now().year
        return f"{_BASE}/informacion-de-la-ani/normatividad?field_tipos_de_normas__tid=All&title=&body_value=&field_fecha__value%5Bvalue%5D%5Byear%5D={current_year}"

    async def fetch_documents(self) -> list[DocumentResult]:
        now = datetime.now()
        years_to_check = [now.year]
        
        # Si es enero, escaneamos también el año pasado para capturar resoluciones tardías.
        if now.month == 1:
            years_to_check.append(now.year - 1)
            
        all_docs = []
        for y in years_to_check:
            url = f"{_BASE}/informacion-de-la-ani/normatividad?field_tipos_de_normas__tid=All&title=&body_value=&field_fecha__value%5Bvalue%5D%5Byear%5D={y}"
            html = await fetch_html(url)
            docs = parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
            all_docs.extend(docs)
            
        return all_docs
