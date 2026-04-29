"""Ministerio del Trabajo scraper — Marco Legal.

La página usa Liferay. Se extrae el listado de documentos del marco
legal visible en la tabla de la biblioteca de documentos.

El sitio Liferay es pesado y tiene analytics continuos, por lo que
`networkidle` NUNCA se alcanza. Usamos `domcontentloaded` + selector wait.
"""
from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult

_BASE = "https://www.mintrabajo.gov.co"
_URL = f"{_BASE}/web/guest/marco-legal"


class MintrabajuScraper(BaseScraper):
    entity_name = "Ministerio del Trabajo"
    entity_url = _URL
    entity_group = "group2_ministerios"
    doc_type_default = "Marco Legal Mintrabajo"
    requires_js = True

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        # Use domcontentloaded instead of networkidle — Liferay never stops pinging
        await page.goto(_URL, timeout=90_000, wait_until="domcontentloaded")

        # Wait for the document library table or links to appear
        try:
            await page.wait_for_selector(
                "a.text-truncate, table tr td a[href*='view_file'], "
                "table tr td a[href*='/documents/']",
                timeout=30_000,
            )
        except Exception:
            pass  # Proceed with whatever loaded

        await page.wait_for_timeout(3_000)

        results: list[DocumentResult] = []

        # Liferay document library: los enlaces de archivos usan .text-truncate
        # dentro de filas de tabla
        links = await page.query_selector_all(
            "a.text-truncate, table tr td a[href*='view_file'], "
            "table tr td a[href*='/documents/']"
        )

        for link in links:
            href = await link.get_attribute("href") or ""
            if not href:
                continue
            # Solo archivos (evitar links de navegación)
            if not any(
                kw in href
                for kw in ("view_file", "/documents/", ".pdf", ".doc")
            ):
                continue

            url = href if href.startswith("http") else f"{_BASE}{href}"
            title = (await link.inner_text()).strip()
            if not title:
                title = (await link.get_attribute("title") or "").strip()
            if not title:
                title = href.split("/")[-1].split("?")[0].replace("+", " ").replace("%20", " ")
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
