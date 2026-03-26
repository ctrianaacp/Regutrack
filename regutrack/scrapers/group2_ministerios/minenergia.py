"""Ministerio de Minas y Energía scraper — Foros de Participación.

El listado de foros es renderizado por JavaScript (React), por lo que
se usa Playwright para obtener el contenido dinámico.
"""
import re
from datetime import date
from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult

_BASE = "https://www.minenergia.gov.co"
_FOROS_URL = f"{_BASE}/es/servicio-al-ciudadano/foros/"

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _parse_fecha_es(text: str) -> date | None:
    """Convierte 'DD de Mes de YYYY' en un objeto date. Retorna None si falla."""
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", text, re.IGNORECASE)
    if not m:
        return None
    day, mes, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    month = _MESES.get(mes)
    if not month:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


class MinenergiaScraper(BaseScraper):
    entity_name = "Ministerio de Minas y Energía"
    entity_url = _FOROS_URL
    entity_group = "group2_ministerios"
    doc_type_default = "Foro MinEnergía"
    requires_js = True  # La página de foros requiere JavaScript (React)

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        await page.goto(_FOROS_URL, timeout=90_000, wait_until="domcontentloaded")
        # Esperar a que carguen las tarjetas de foros (React SPA — nunca llega a networkidle)
        await page.wait_for_selector("h4.news-list-item-title", timeout=30_000)
        await page.wait_for_timeout(1_500)

        results: list[DocumentResult] = []

        # Cada foro es un bloque con un <a> que envuelve el título y fechas
        entries = await page.query_selector_all("h4.news-list-item-title")

        for h4 in entries:
            # Título
            title = (await h4.inner_text()).strip()
            if not title:
                continue

            # El <a> ancestro contiene el href del foro
            link_el = await h4.evaluate_handle("(el) => el.closest('a')")
            href = await link_el.get_attribute("href") if link_el else None
            url = (
                href if href and href.startswith("http")
                else f"{_BASE}{href}"
            ) if href else _FOROS_URL

            # Fecha de inicio, extraída del párrafo hermano con "Fecha Inicio:"
            parent = await h4.evaluate_handle(
                "(el) => el.closest('a') || el.parentElement"
            )
            fecha_inicio: date | None = None
            date_raw = ""
            try:
                date_el = await parent.query_selector("p:has-text('Fecha Inicio')")
                if date_el:
                    raw = (await date_el.inner_text()).strip()
                    # Formato: "Fecha Inicio: DD de Mes de YYYY / Fecha Fin: ..."
                    date_raw = raw.split("/")[0].replace("Fecha Inicio:", "").strip()
                    fecha_inicio = _parse_fecha_es(date_raw)
            except Exception:
                pass

            results.append(
                DocumentResult(
                    title=title,
                    url=url,
                    doc_type=self.doc_type_default,
                    publication_date=fecha_inicio,
                    raw_summary=date_raw or None,
                )
            )

        return results
