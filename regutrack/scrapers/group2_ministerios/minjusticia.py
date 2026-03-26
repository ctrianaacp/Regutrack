"""Ministerio de Justicia y del Derecho scraper — Resoluciones.

El sitio usa SharePoint/Bootstrap con acordeones por año.
Se expande el acordeón del año vigente para extraer las resoluciones más
recientes.
"""
import datetime
from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult

_BASE = "https://www.minjusticia.gov.co"
_URL = f"{_BASE}/normatividad-co/Paginas/Resoluciones.aspx"
_CURRENT_YEAR = datetime.date.today().year


class MinjusticiaScraper(BaseScraper):
    entity_name = "Ministerio de Justicia y del Derecho"
    entity_url = _URL
    entity_group = "group2_ministerios"
    doc_type_default = "Resolución Minjusticia"
    requires_js = True

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        await page.goto(_URL, timeout=45_000, wait_until="networkidle")
        await page.wait_for_timeout(2_000)

        results: list[DocumentResult] = []

        # Intentar expandir el acordeón del año vigente
        year_str = str(_CURRENT_YEAR)
        try:
            btn = await page.query_selector(
                f"button.btn-link:has-text('{year_str}')"
            )
            if btn:
                is_expanded = await btn.get_attribute("aria-expanded")
                if is_expanded != "true":
                    await btn.click()
                    await page.wait_for_timeout(1_000)
        except Exception:
            pass

        # Extraer todos los enlaces de descarga PDF visibles
        links = await page.query_selector_all(
            "a.btn-outline-marine, a[class*='btn-outline']"
        )
        for link in links:
            href = await link.get_attribute("href") or ""
            if not href:
                continue
            url = href if href.startswith("http") else f"{_BASE}{href}"

            # Título: atributo title del enlace, o el span/texto anterior
            title = (await link.get_attribute("title") or "").strip()
            if not title:
                # Intenta el h4/párrafo hermano más cercano
                try:
                    parent = await link.evaluate_handle(
                        "(el) => el.closest('li') || el.closest('div') || el.parentElement"
                    )
                    heading = await parent.query_selector("h4, h5, span, p")
                    if heading:
                        title = (await heading.inner_text()).strip()
                except Exception:
                    pass
            if not title:
                # Construir desde el href
                title = href.split("/")[-1].replace("-", " ").replace(".pdf", "").strip()
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
