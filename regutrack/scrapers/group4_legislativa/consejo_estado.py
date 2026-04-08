"""Consejo de Estado scraper."""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_BASE = "https://www.consejodeestado.gov.co"

MONTHS_ES = {
    "01": "MARZO", "02": "FEBRERO", "03": "MARZO", "04": "ABRIL",
    "05": "MAYO", "06": "JUNIO", "07": "JULIO", "08": "AGOSTO",
    "09": "SEPTIEMBRE", "10": "OCTUBRE", "11": "NOVIEMBRE", "12": "DICIEMBRE"
}
# Fix dictionary initialization
MONTHS_ES["01"] = "ENERO"

class ConsejoEstadoScraper(BaseScraper):
    entity_name = "Consejo de Estado"
    entity_url = f"{_BASE}/actos-administrativos/conexion2.php"
    entity_group = "group4_legislativa"
    doc_type_default = "Acto Administrativo"

    def _format_title(self, doc_type: str, number: str, date_str: str) -> str:
        """
        Construye el título con el formato legal de la entidad:
        DECRETO NÚMERO 249 DE 2026 (26 DE MARZO)
        """
        try:
            year, month, day = date_str.split("-")
        except ValueError:
            # Fallback en caso de que la fecha venga malformada
            return f"{doc_type.upper()} NÚMERO {number}".strip()
            
        month_name = MONTHS_ES.get(month, "")
        
        # Convertir a entero para quitar posibles ceros a la izquierda en el día
        title = f"{doc_type.upper()} NÚMERO {number} DE {year} ({int(day)} DE {month_name})"
        return title.strip()

    async def fetch_documents(self) -> list[DocumentResult]:
        # El origen de datos directo desde el iframe de Actos Administrativos
        html = await fetch_html(self.entity_url)
        soup = BeautifulSoup(html, "html.parser")
        
        # La tabla DataTables donde están estructurados los documentos
        rows = soup.select("table#example tbody tr")
        
        results = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue
                
            # Extraer las columnas
            pub_date_full = cols[0].get_text(strip=True)
            doc_type = cols[1].get_text(strip=True)
            number = cols[2].get_text(strip=True)
            date_acto = cols[3].get_text(strip=True) # Formato YYYY-MM-DD
            
            a_tag = cols[4].find("a", href=True)
            url = urljoin(self.entity_url, a_tag["href"]) if a_tag else ""
            
            # Formateamos el título usando la lógica aprobada
            title = self._format_title(doc_type, number, date_acto)
            
            if not title or not url:
                continue

            results.append(
                DocumentResult(
                    title=title,
                    url=url,
                    # Usamos la fecha del acto u la fecha de publicación extraída
                    publication_date=date_acto or pub_date_full.split(" ")[0],
                    doc_type=doc_type.capitalize() if doc_type else self.doc_type_default,
                    raw_summary="Extracto automatizado desde Biblioteca Digital - Actos administrativos de Consejo de Estado."
                )
            )
            
        return results
