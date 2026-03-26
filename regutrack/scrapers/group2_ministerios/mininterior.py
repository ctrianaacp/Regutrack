"""Ministerio del Interior scraper — Normatividad.

La página usa Divi Machine / WordPress con JS. Contiene ~15 000 documentos
con paginación. Este scraper extrae solo la primera página (documentos más
recientes) para capturar novedades.
"""
from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult

_BASE = "https://www.mininterior.gov.co"
_URL = f"{_BASE}/normatividad/"


class MininteriorScraper(BaseScraper):
    entity_name = "Ministerio del Interior"
    entity_url = _URL
    entity_group = "group2_ministerios"
    doc_type_default = "Resolución Mininterior"
    requires_js = True

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        await page.goto(_URL, timeout=45_000, wait_until="networkidle")
        await page.wait_for_selector("div.dmach-grid-item", timeout=20_000)
        await page.wait_for_timeout(1_500)

        results: list[DocumentResult] = []

        items = await page.query_selector_all("div.dmach-grid-item")
        for item in items:
            # Título del documento
            title_el = await item.query_selector("h4")
            title = (await title_el.inner_text()).strip() if title_el else ""
            if not title:
                continue

            # PDF directo
            pdf_el = await item.query_selector("a.dmach-acf-value, a.et_pb_button")
            href = await pdf_el.get_attribute("href") if pdf_el else None
            url = href if href else _URL

            # Fecha (vigencia)
            date_text = ""
            try:
                fecha_el = await item.query_selector(
                    "p:has-text('Fecha de entrada'), p:has-text('Fecha vigencia')"
                )
                if fecha_el:
                    date_text = (
                        (await fecha_el.inner_text())
                        .split(":")[-1]
                        .strip()
                    )
            except Exception:
                pass

            results.append(
                DocumentResult(
                    title=title,
                    url=url,
                    doc_type=self.doc_type_default,
                    raw_summary=date_text or None,
                )
            )

        return results
