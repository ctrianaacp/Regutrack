"""ANE — Agencia Nacional del Espectro scraper.

El sitio ANE (SharePoint Online) requiere JavaScript para renderizar.
Se usa Playwright para obtener el HTML completo antes de parsear.
"""
from regutrack.scrapers.base import BaseScraper
from regutrack.scrapers.common import parse_standard_normatividad_page
from regutrack.utils.hashing import DocumentResult

_BASE = "https://www.ane.gov.co"

# Phrases that indicate we got a JS-error page instead of real content
_JS_ERROR_PHRASES = [
    "javascript habilitado",
    "javascript enabled",
    "enable javascript",
    "you need to enable javascript",
    "please enable javascript",
]


class ANEScraper(BaseScraper):
    entity_name = "Agencia Nacional del Espectro (ANE)"
    entity_url = f"{_BASE}/SitePages/Normatividad.aspx"
    entity_group = "group5_agencias"
    doc_type_default = "Resolución ANE"
    requires_js = True      # SharePoint Online needs JS rendering

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        await page.goto(self.entity_url, timeout=60_000, wait_until="domcontentloaded")
        # Wait for any normatividad container — SharePoint never reaches networkidle
        try:
            await page.wait_for_selector(
                "table, .ms-rtestate-field, [class*='normatividad'], [class*='Normatividad']",
                timeout=30_000,
            )
        except Exception:
            pass  # Proceed anyway; parse whatever loaded
        await page.wait_for_timeout(2000)
        html = await page.content()
        return parse_standard_normatividad_page(html, _BASE, self.doc_type_default)
