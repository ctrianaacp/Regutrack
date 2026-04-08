"""Senado de la República scraper — Proyectos de Ley."""
from datetime import datetime
import httpx

from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult

_BASE = "https://leyes.senado.gov.co"
_API  = f"{_BASE}/api/search_pdly.php"
_PAGE = f"{_BASE}/#pdly"

class SenadoScraper(BaseScraper):
    entity_name = "Senado de la República"
    entity_url = _PAGE
    entity_group = "group4_legislativa"
    doc_type_default = "Proyecto de Ley"

    async def fetch_documents(self) -> list[DocumentResult]:
        """
        Consulta la API de leyes.senado.gov.co para obtener los Proyectos de Ley.
        Usa un POST multipart/form-data que es lo que el servidor espera empíricamente.
        """
        results: list[DocumentResult] = []

        now = datetime.now()
        # Puedes enviar algún campo en el multipart, usando un dict vacío explota en httpx,
        # así que enviamos una consulta de búsqueda vacía o el año.
        files = {"search": (None, "")}

        async with httpx.AsyncClient(timeout=60, verify=False, follow_redirects=True) as client:
            try:
                resp = await client.post(_API, files=files)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                # Si falla la red local (ej. bloqueos geográficos o IP), retornamos vacío
                # para que el pipeline principal no crashee por completo.
                print(f"[SenadoScraper] Error fetching API: {e}")
                return []

        items = data if isinstance(data, list) else data.get("data", [])
        for item in items:
            numero = item.get("numero_senado") or item.get("numero") or ""
            camara = item.get("numero_camara", "")
            titulo = (item.get("titulo") or "").strip()
            autor  = (item.get("autor") or "").strip()
            cuatrenio = item.get("cuatrenio") or item.get("anio") or ""
            estado = item.get("estado") or ""

            if not titulo:
                continue

            num_completo = str(numero)
            if camara and str(camara) != "-":
                num_completo += f" / {camara}"

            title = f"PROYECTO DE LEY {num_completo} – {titulo[:200]}"
            pid = item.get("id") or ""
            url = f"{_BASE}/api/get_detalle_pdly.php?id={pid}" if pid else _PAGE

            results.append(
                DocumentResult(
                    title=title.strip()[:300],
                    url=url,
                    doc_type="Proyecto de Ley",
                    number=num_completo,
                    publication_date=now.strftime("%Y-%m-%d"),  # El JSON puede no traer fecha exacta de pub, usar fecha actual o derivar
                    raw_summary=f"Autor: {autor} | Estado: {estado} | Cuatrenio: {cuatrenio}"[:500],
                )
            )

        return results
