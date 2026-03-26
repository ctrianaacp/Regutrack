"""LLM Extractor — uses OpenAI to extract regulatory documents from arbitrary HTML.

Flow:
  1. Receive raw HTML from a scraper that returned 0 docs or failed.
  2. Clean and truncate the HTML to stay within token limits.
  3. Send to OpenAI with a structured JSON-output prompt.
  4. Parse the LLM response into list[DocumentResult].
  5. Optionally return the discovered CSS selectors for learned-selector persistence.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any

from regutrack.utils.hashing import DocumentResult

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """Eres un experto extractor de información normativa de páginas web del gobierno colombiano.
Tu tarea es analizar el HTML de una página y extraer todos los documentos normativos
(leyes, decretos, resoluciones, circulares, acuerdos, autos, sentencias, etc.) que aparezcan.

Responde ÚNICAMENTE con un objeto JSON válido con esta estructura:
{
  "documents": [
    {
      "title": "Título completo del documento",
      "url": "URL del documento individual (PDF, página de detalle, etc.) — NO la URL del listado",
      "doc_type": "Tipo: Ley | Decreto | Resolución | Circular | Acuerdo | Sentencia | Auto | Reglamento | Concepto | Directiva | Otro",
      "number": "Número o identificador del documento (string o null)",
      "publication_date": "Fecha en formato YYYY-MM-DD (string o null)"
    }
  ],
  "selectors": {
    "list_container": "Selector CSS del contenedor principal de la lista de documentos",
    "item_row": "Selector CSS de cada fila/ítem con un documento",
    "title_element": "Selector CSS del elemento con el título dentro de cada ítem",
    "link_element": "Selector CSS del elemento <a> con el link dentro de cada ítem",
    "date_element": "Selector CSS del elemento con la fecha dentro de cada ítem (o null si no existe)"
  },
  "confidence": 0.0
}

REGLAS CRÍTICAS SOBRE URLs:
- El campo "url" DEBE ser el enlace directo al documento individual:
  * Si hay un enlace a un PDF → usa esa URL del PDF
  * Si hay un enlace a una página de detalle del document → usa esa URL
  * Si hay múltiples links en una fila, usa el que apunte al documento específico (no a categorías o navegación)
- Si NO encuentras un URL específico para ese documento → usa null (NO uses la URL de la página de listado)
- NUNCA uses la URL base/listado como URL de un documento específico

REGLAS GENERALES:
- Incluye SOLO documentos normativos reales, no menús ni elementos de navegación.
- Si un campo no existe en la página, usa null.
- El campo "confidence" va de 0.0 a 1.0 indicando tu confianza en los resultados.
- Si la página no tiene documentos normativos identificables, devuelve {"documents": [], "selectors": null, "confidence": 0.0}.
- Extrae TODOS los documentos visibles, no solo los primeros.
- Para URLs relativas, indícalas tal como aparecen en el href del <a> (el sistema las resolverá).
"""



def _clean_html(html: str, max_chars: int) -> str:
    """Remove scripts, styles, SVGs and truncate to max_chars."""
    for pattern in [
        r"<script[^>]*>.*?</script>",
        r"<style[^>]*>.*?</style>",
        r"<svg[^>]*>.*?</svg>",
        r"<!--.*?-->",
        r"<noscript[^>]*>.*?</noscript>",
    ]:
        html = re.sub(pattern, " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"\s{3,}", " ", html)
    return html[:max_chars]


# Phrases that indicate a JS-required error page — no real content to extract
_JS_ERROR_PHRASES = [
    "javascript habilitado",
    "javascript enabled",
    "enable javascript",
    "you need to enable javascript",
    "please enable javascript",
    "sin_título",           # SharePoint blank page artifact
    "sin título",
]


def _is_js_error_page(html: str) -> bool:
    """Return True if the HTML is a JS-disabled error page with no real content."""
    lower = html.lower()
    matches = sum(1 for phrase in _JS_ERROR_PHRASES if phrase in lower)
    # Also check if actual content text is very short (< 500 visible chars after cleaning)
    visible_text = re.sub(r"<[^>]+>", " ", html)
    visible_text = re.sub(r"\s+", " ", visible_text).strip()
    if matches >= 1 and len(visible_text) < 800:
        return True
    return False



def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            from datetime import datetime
            return datetime.strptime(raw.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _resolve_url(raw_url: str | None, base_url: str) -> str | None:
    if not raw_url:
        return None
    raw_url = raw_url.strip()
    if raw_url.startswith("http"):
        return raw_url
    if raw_url.startswith("//"):
        return "https:" + raw_url
    from urllib.parse import urljoin
    return urljoin(base_url, raw_url)


class LLMExtractor:
    """Extracts DocumentResult objects from raw HTML using OpenAI."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.model = model
        self._client = None
        self._api_key = api_key

    def _get_client(self):
        """Lazy init of OpenAI client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    async def extract(
        self,
        html: str,
        entity_name: str,
        entity_url: str,
        max_chars: int = 80_000,
    ) -> tuple[list[DocumentResult], dict[str, Any] | None]:
        """
        Extract documents from HTML using the LLM.

        Returns:
            (documents, selectors_dict)  — selectors may be None if LLM didn't provide them.
        """
        clean = _clean_html(html, max_chars)
        if len(clean) < 200:
            logger.warning(f"[AI] HTML too short after cleaning for {entity_name}: {len(clean)} chars")
            return [], None

        # Reject JS-error pages (e.g. SharePoint without Playwright)
        if _is_js_error_page(html):
            logger.warning(
                f"[AI] Skipping {entity_name}: page requires JavaScript "
                f"(got JS-error page). Set requires_js=True on the scraper."
            )
            return [], None

        user_prompt = (
            f"Entidad: {entity_name}\n"
            f"URL base: {entity_url}\n\n"
            f"HTML de la página:\n```html\n{clean}\n```"
        )

        logger.info(f"[AI] Sending HTML ({len(clean)} chars) to {self.model} for {entity_name}")

        try:
            client = self._get_client()
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=8192,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                ),
            )
            raw_text = response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"[AI] OpenAI API error for {entity_name}: {e}")
            return [], None

        # Parse JSON response
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    logger.error(f"[AI] Could not parse LLM JSON for {entity_name}: {raw_text[:200]}")
                    return [], None
            else:
                logger.error(f"[AI] Invalid JSON from LLM for {entity_name}: {raw_text[:200]}")
                return [], None

        confidence = data.get("confidence", 0.0)
        raw_docs = data.get("documents", [])
        selectors = data.get("selectors", None)

        logger.info(
            f"[AI] {entity_name}: {len(raw_docs)} docs extracted, "
            f"confidence={confidence:.2f}, model={self.model}"
        )

        documents: list[DocumentResult] = []
        seen_urls: set[str] = set()

        for item in raw_docs:
            title = (item.get("title") or "").strip()
            if not title:
                continue

            url = _resolve_url(item.get("url"), entity_url)
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)

            doc = DocumentResult(
                title=title[:300],
                url=url or entity_url,
                doc_type=item.get("doc_type") or None,
                number=(item.get("number") or "").strip() or None,
                publication_date=_parse_date(item.get("publication_date")),
                raw_summary=title[:500],
            )

            if doc.is_valid():
                documents.append(doc)

        return documents, selectors
