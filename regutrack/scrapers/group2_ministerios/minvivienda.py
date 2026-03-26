"""Ministerio de Vivienda, Ciudad y Territorio scraper — Normativa.

El sitio usa Drupal Views con JS. Cada resolución aparece en un
div.views-row con título, fecha y enlace al PDF.
"""
import re
from datetime import date
from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult

_BASE = "https://minvivienda.gov.co"
_URL = f"{_BASE}/normativa"


def _parse_fecha_ddmmyyyy(text: str) -> date | None:
    """Convierte 'DD/MM/AAAA' en date. Retorna None si falla."""
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


class MinviviendaScraper(BaseScraper):
    entity_name = "Ministerio de Vivienda, Ciudad y Territorio"
    entity_url = _URL
    entity_group = "group2_ministerios"
    doc_type_default = "Norma Minvivienda"
    requires_js = True

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        await page.goto(_URL, timeout=90_000, wait_until="domcontentloaded")
        await page.wait_for_selector("div.views-row", timeout=30_000)
        await page.wait_for_timeout(1_500)

        results: list[DocumentResult] = []

        rows = await page.query_selector_all("div.views-row")
        for row in rows:
            # Título
            title_el = await row.query_selector(".views-field-title a")
            if not title_el:
                title_el = await row.query_selector("a")
            title = (await title_el.inner_text()).strip() if title_el else ""
            if not title:
                continue

            # PDF o enlace al documento
            pdf_el = await row.query_selector(".views-field-field-archivo a")
            href = await pdf_el.get_attribute("href") if pdf_el else None
            if not href:
                href = await title_el.get_attribute("href") if title_el else None
            url = (
                href if href and href.startswith("http")
                else f"{_BASE}{href}"
            ) if href else _URL

            # Fecha de la norma (DD/MM/AAAA)
            fecha: date | None = None
            raw_fecha = ""
            try:
                fecha_el = await row.query_selector(".views-field-field-fecha-norma")
                if fecha_el:
                    raw_fecha = (await fecha_el.inner_text()).strip()
                    fecha = _parse_fecha_ddmmyyyy(raw_fecha)
            except Exception:
                pass

            results.append(
                DocumentResult(
                    title=title,
                    url=url,
                    doc_type=self.doc_type_default,
                    publication_date=fecha,
                    raw_summary=raw_fecha or None,
                )
            )

        return results
