"""UPME — Unidad de Planeación Minero Energética scraper.

Combina tres páginas de la biblioteca jurídica UPME:
  1. Resoluciones
  2. Circulares
  3. Proyectos Normativos del año en curso

Todas las páginas usan Elementor/WordPress con contenido dinámico.
"""
import datetime
from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult

_BASE = "https://www.upme.gov.co"
_CURRENT_YEAR = datetime.date.today().year

_URLS = [
    (f"{_BASE}/nosotros/biblioteca-juridica/resoluciones-upme/", "Resolución UPME"),
    (f"{_BASE}/nosotros/biblioteca-juridica/circulares-upme/", "Circular UPME"),
    (
        f"{_BASE}/nosotros/biblioteca-juridica/proyectos-normativos-upme/"
        f"proyectos-normativos-{_CURRENT_YEAR}/",
        "Proyecto Normativo UPME",
    ),
]


class UPMEScraper(BaseScraper):
    entity_name = "Unidad de Planeación Minero Energética (UPME)"
    entity_url = f"{_BASE}/nosotros/biblioteca-juridica/"
    entity_group = "group6_descentralizadas"
    doc_type_default = "Normativa UPME"
    requires_js = True

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        results: list[DocumentResult] = []

        for url, doc_type in _URLS:
            await page.goto(url, timeout=90_000, wait_until="domcontentloaded")
            # Wait for Elementor buttons or consultar links — WP never reaches networkidle
            try:
                await page.wait_for_selector(
                    "a.btn-dark, a[class*='btn-dark'], a.elementor-button, "
                    "a[class*='elementor-button-link']",
                    timeout=30_000,
                )
            except Exception:
                pass  # Some sub-pages may have no buttons; continue anyway

            # --- Botones "Consultar" (resoluciones y circulares) ---
            consultar_links = await page.query_selector_all(
                "a.btn.btn-dark, a[class*='btn-dark']"
            )
            for link in consultar_links:
                text = (await link.inner_text()).strip()
                if "consultar" not in text.lower() and "ver" not in text.lower():
                    continue
                href = await link.get_attribute("href") or ""
                if not href:
                    continue

                # Título: bloque padre → busca heading/párrafo cercano
                card = await link.evaluate_handle(
                    "(el) => el.closest('.elementor-widget-wrap') "
                    "|| el.closest('.card') || el.parentElement"
                )
                title = ""
                try:
                    h_el = await card.query_selector("h2,h3,h4,h5,strong,b")
                    if h_el:
                        title = (await h_el.inner_text()).strip()
                except Exception:
                    pass
                if not title:
                    title = text  # fallback al texto del botón

                results.append(
                    DocumentResult(
                        title=title,
                        url=href if href.startswith("http") else f"{_BASE}{href}",
                        doc_type=doc_type,
                    )
                )

            # --- Botones Elementor (proyectos normativos) ---
            elementor_links = await page.query_selector_all(
                "a.elementor-button, a[class*='elementor-button-link']"
            )
            for link in elementor_links:
                href = await link.get_attribute("href") or ""
                if not href or not ("docs.upme.gov.co" in href or ".pdf" in href.lower()):
                    continue

                # aria-label suele tener el nombre completo del documento
                aria = await link.get_attribute("aria-label") or ""
                title = aria.replace("Ver documento:", "").strip()
                if not title:
                    title = (await link.inner_text()).strip()
                if not title:
                    title = href.split("/")[-1].replace("_", " ").replace(".pdf", "")

                results.append(
                    DocumentResult(
                        title=title,
                        url=href,
                        doc_type=doc_type,
                    )
                )

        # Deduplicar por URL
        seen: set[str] = set()
        unique = []
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        return unique
