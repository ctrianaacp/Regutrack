"""Procuraduría General de la Nación scraper.

Utiliza el endpoint interno de la Relatoría (apps.procuraduria.gov.co),
que es el mismo que se incrusta como iframe en la página de normatividad.
No requiere reCAPTCHA — un POST simple con el año retorna la lista de documentos.

Nota: La Procuraduría ha cambiado su portal de normatividad. Ahora la sección
de "Normativa" solo muestra un texto descriptivo y un enlace a
"Resoluciones, Circulares, Directivas y otros", no una tabla de datos parseables
vía POST.  El scraper ahora consume también el endpoint de Resoluciones para
obtener documentos reales.
"""
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult

_BASE = "https://www.procuraduria.gov.co"
_RELATORIA_BASE = "https://apps.procuraduria.gov.co/relatoria"

# Endpoint de Normatividad
_ENDPOINT_NORMATIVIDAD = (
    f"{_RELATORIA_BASE}/index.jsp"
    "?option=co.gov.pgn.relatoria.frontend.component.pagefactory.NormatividadPageFactory"
)

# Endpoint de Resoluciones, Circulares, Directivas
_ENDPOINT_RESOLUCIONES = (
    f"{_RELATORIA_BASE}/index.jsp"
    "?option=co.gov.pgn.relatoria.frontend.component.pagefactory.PirelResolucionesPageFactory"
)


class ProcuradoriaScraper(BaseScraper):
    entity_name = "Procuraduría General de la Nación"
    entity_url = _ENDPOINT_NORMATIVIDAD          # URL informativa para la UI
    entity_group = "group3_control"
    doc_type_default = "Directiva Procuraduría"

    async def fetch_documents(self) -> list[DocumentResult]:
        now = datetime.now()
        years = [now.year]
        # Si es enero incluimos también el año anterior para no perder documentos tardíos
        if now.month == 1:
            years.append(now.year - 1)

        all_docs: list[DocumentResult] = []
        for year in years:
            for endpoint in [_ENDPOINT_NORMATIVIDAD, _ENDPOINT_RESOLUCIONES]:
                docs = await self._fetch_year(year, endpoint)
                all_docs.extend(docs)

        # Deduplicar por (título, url)
        seen: set[tuple] = set()
        result = []
        for d in all_docs:
            key = (d.title.lower()[:60], d.url)
            if key not in seen and d.is_valid():
                seen.add(key)
                result.append(d)

        return result

    async def _fetch_year(self, year: int, endpoint: str) -> list[DocumentResult]:
        """Hace POST al endpoint de la Relatoría con el año dado y parsea los resultados."""
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            verify=False,  # SSL cert issues on .gov.co
        ) as client:
            try:
                resp = await client.post(endpoint, data={"anio": str(year), "ok": "Buscar"})
                resp.raise_for_status()
                html = resp.text
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (502, 503, 504):
                    return []  # Server temporarily unavailable
                raise
            except Exception:
                return []

        soup = BeautifulSoup(html, "html.parser")

        # La tabla más grande (más filas) es la de resultados
        tables = soup.find_all("table")
        if not tables:
            return []

        results_table = max(tables, key=lambda t: len(t.find_all("tr")))
        rows = results_table.find_all("tr")

        docs: list[DocumentResult] = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            doc_type = cols[0].get_text(strip=True) if len(cols) > 0 else ""
            number    = cols[1].get_text(strip=True) if len(cols) > 1 else ""
            summary   = cols[2].get_text(strip=True) if len(cols) > 2 else ""

            # Buscar enlace al documento
            a_tag = row.find("a", href=True)
            url = urljoin(_BASE, a_tag["href"]) if a_tag else None

            # Construir título "TIPO NÚMERO DE AÑO" similar a otras entidades
            parts = [doc_type.upper()]
            if number:
                parts.append(number)
            parts.append(f"DE {year}")
            title = " ".join(parts)

            if not title or not url:
                continue

            docs.append(
                DocumentResult(
                    title=title.strip()[:300],
                    url=url,
                    doc_type=doc_type.capitalize() if doc_type else self.doc_type_default,
                    number=number,
                    publication_date=None,
                    raw_summary=summary[:500],
                )
            )

        return docs
