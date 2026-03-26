"""CREG — Comisión de Regulación de Energía y Gas scraper.

El gestor normativo de la CREG renderiza con JavaScript.
Se usa Playwright para obtener el listado cronológico de resoluciones.
"""
from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult

_BASE = "https://gestornormativo.creg.gov.co/gestor/entorno"
_LIST_URL = f"{_BASE}/resoluciones_por_orden_cronologico.html"


class CREGScraper(BaseScraper):
    entity_name = "Comisión de Regulación de Energía y Gas (CREG)"
    entity_url = _LIST_URL
    entity_group = "group5_agencias"
    doc_type_default = "Resolución CREG"
    requires_js = True

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        await page.goto(_LIST_URL, timeout=45_000, wait_until="networkidle")
        await page.wait_for_timeout(2_000)

        results: list[DocumentResult] = []

        # Cada resolución es un <a href="docs/..."> dentro del panel de lista
        entries = await page.query_selector_all("a[href^='docs/']")

        for entry in entries:
            href = await entry.get_attribute("href") or ""
            url = f"{_BASE}/{href}" if href else _LIST_URL

            # Título: primer div de texto dentro del enlace (excluye .ver-mas-opcion-nueva)
            title_el = await entry.query_selector("div > div:not(.ver-mas-opcion-nueva)")
            if not title_el:
                title_el = entry
            title = (await title_el.inner_text()).strip().split("\n")[0].strip()
            if not title:
                continue

            results.append(
                DocumentResult(
                    title=title,
                    url=url,
                    doc_type=self.doc_type_default,
                )
            )

        return results
