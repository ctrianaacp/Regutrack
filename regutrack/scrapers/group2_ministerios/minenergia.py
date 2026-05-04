"""Ministerio de Minas y Energía scraper — Normatividad (normativame.minenergia.gov.co).

Apunta al Sistema de Información Normativa (Nexura) que expone los decretos,
resoluciones y circulares vigentes.  La página principal lista los documentos
más recientes vía un endpoint PHP que devuelve HTML con una tabla/cards.

El portal genera URLs de descarga con un sufijo numérico aleatorio en /tmp/,
por lo que la URL NO se incluye en el hash de deduplicación — se usa
title + number + doc_type para crear un hash estable.
"""

import re
from datetime import date
from bs4 import BeautifulSoup

from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult
from regutrack.utils.http_client import fetch_html

_NORMATIVA_URL = (
    "https://normativame.minenergia.gov.co/loader.php"
    "?lServicio=Normatividad&lTipo=User&lFuncion=avanzado"
)
_BASE = "https://normativame.minenergia.gov.co"

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _parse_fecha_es(text: str) -> date | None:
    """Convierte 'DD de Mes de YYYY' en date.  Retorna None si falla."""
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


def _normalize_url(href: str) -> str:
    """Construye una URL absoluta y corrige errores comunes del portal."""
    if not href:
        return ""
    href = href.strip()
    if href.startswith("http"):
        # Fix the missing '/' between domain and path that the portal sometimes produces
        href = href.replace(
            "normativame.minenergia.gov.copublic_html",
            "normativame.minenergia.gov.co/public_html",
        )
        return href
    return f"{_BASE}/{href.lstrip('/')}"


def _stable_hash_key(title: str, number: str | None, doc_type: str | None) -> str:
    """Build a URL-independent key for hashing to avoid duplicates from random PDF suffixes."""
    import hashlib
    raw = "|".join([
        (title or "").strip().lower(),
        (number or "").strip().lower(),
        (doc_type or "").strip().lower(),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class MinenergiaScraper(BaseScraper):
    entity_name = "Ministerio de Minas y Energía"
    entity_url = _NORMATIVA_URL
    entity_group = "group2_ministerios"
    doc_type_default = "Norma"
    requires_js = True  # The Nexura portal renders via JS

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        await page.goto(_NORMATIVA_URL, timeout=90_000, wait_until="domcontentloaded")

        # Wait for the normative table/cards to render
        try:
            await page.wait_for_selector("table, .listado, .card, .resultado", timeout=30_000)
        except Exception:
            pass  # Fall through — we'll try to parse whatever loaded
        await page.wait_for_timeout(2_000)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        results: list[DocumentResult] = []
        seen_keys: set[str] = set()

        # Strategy 1: Look for table rows (common Nexura layout)
        for row in soup.select("table tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            # Try to extract: doc_type, number, title/description, date, link
            texts = [c.get_text(strip=True) for c in cells]
            link_el = row.find("a", href=True)
            href = link_el["href"] if link_el else ""

            doc_type = texts[0] if texts[0] else self.doc_type_default
            number = texts[1] if len(texts) > 1 else None
            title = texts[2] if len(texts) > 2 else texts[0]
            pub_date = None
            if len(texts) > 3:
                pub_date = _parse_fecha_es(texts[3])

            if not title or len(title) < 3:
                continue

            # Use stable key (without URL) to prevent duplicates
            key = _stable_hash_key(title, number, doc_type)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            results.append(DocumentResult(
                title=title,
                url=_normalize_url(href),
                doc_type=doc_type,
                number=number,
                publication_date=pub_date,
                raw_summary=f"Normativa del Ministerio de Minas y Energía.",
            ))

        # Strategy 2: Look for card/list items if no table found
        if not results:
            for card in soup.select(".card, .listado-item, .resultado, .item-normativa"):
                title_el = card.find(["h3", "h4", "h5", "a", "strong"])
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not title or len(title) < 3:
                    continue

                link_el = card.find("a", href=True)
                href = link_el["href"] if link_el else ""

                # Try to extract doc type and number from title
                doc_type = self.doc_type_default
                number = None
                type_match = re.match(
                    r"(Decreto|Resolución|Circular|Ley|Acuerdo)\s+(?:No\.?\s*)?(\S+)",
                    title, re.IGNORECASE,
                )
                if type_match:
                    doc_type = type_match.group(1).capitalize()
                    number = type_match.group(2)

                # Look for date in card text
                card_text = card.get_text(" ", strip=True)
                pub_date = _parse_fecha_es(card_text)

                key = _stable_hash_key(title, number, doc_type)
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                results.append(DocumentResult(
                    title=title,
                    url=_normalize_url(href),
                    doc_type=doc_type,
                    number=number,
                    publication_date=pub_date,
                    raw_summary=f"Normativa del Ministerio de Minas y Energía.",
                ))

        return results
