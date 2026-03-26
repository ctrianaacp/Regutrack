"""Shared helper for scraping standard 'Normatividad' sections in .gov.co sites.

Most Colombian government ministry/agency sites follow a template where
normative documents appear in the Transparency section under
/normatividad, /transparencia/normatividad, or similar paths.
"""

import re
from datetime import date
from typing import Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag

from regutrack.utils.hashing import DocumentResult


# Common CSS selectors that appear on the standard Gov Colombia template
_SELECTORS = [
    "table.tablaResultados tr",
    "table.views-table tr",
    "div.view-content .views-row",
    "ul.listado-normas li",
    "div.item-list li",
    "article.node",
    "table tr",
]

# Link text patterns that are NOT document links (nav, pagination, etc.)
_SKIP_LINK_TEXT = re.compile(
    r"^(inicio|home|siguiente|anterior|next|prev|\d+|ver más|more|subir|volver|login|"
    r"buscar|search|menu|contáctenos|english)$",
    re.IGNORECASE,
)

# File extensions that are clearly document links
_DOC_EXTENSIONS = re.compile(
    r"\.(pdf|doc|docx|xls|xlsx|ppt|pptx|odt)(\?.*)?$",
    re.IGNORECASE,
)


def _resolve_url(href: str, base_url: str) -> str | None:
    """Resolve a potentially relative URL against the base. Returns None if empty."""
    if not href:
        return None
    href = href.strip()
    if href.startswith(("javascript:", "#", "mailto:")):
        return None
    if href.startswith("//"):
        scheme = urlparse(base_url).scheme or "https"
        return f"{scheme}:{href}"
    if href.startswith("http"):
        return href
    # Relative URL
    try:
        return urljoin(base_url, href)
    except Exception:
        return None


def _best_link(row: Tag, base_url: str) -> str | None:
    """
    Find the most relevant document link in a table row / list item.

    Priority:
    1. Any <a> whose href ends with a document extension (.pdf, .doc, etc.)
    2. Any <a> that contains a keyword matching a norm type in its href or text
    3. First <a> with a non-empty href that is not a navigation link
    """
    anchors = row.find_all("a", href=True)

    # 1. Document file extension
    for a in anchors:
        href = a.get("href", "")
        if _DOC_EXTENSIONS.search(href):
            return _resolve_url(href, base_url)

    # 2. Norm-keyword in href or link text
    norm_pattern = re.compile(
        r"(decreto|resoluci[oó]n|circular|ley|acuerdo|directiva|auto|sentencia|"
        r"providencia|concepto|instrucci[oó]n|norma|documento|archivo|anexo)",
        re.IGNORECASE,
    )
    for a in anchors:
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if norm_pattern.search(href) or norm_pattern.search(text):
            resolved = _resolve_url(href, base_url)
            if resolved:
                return resolved

    # 3. First non-navigation anchor
    for a in anchors:
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if _SKIP_LINK_TEXT.match(text):
            continue
        resolved = _resolve_url(href, base_url)
        if resolved:
            return resolved

    return None   # No usable link found — do NOT fall back to the listing page


def parse_standard_normatividad_page(
    html: str, base_url: str, default_doc_type: str = "Norma"
) -> list[DocumentResult]:
    """
    Generic parser for the standard Colombian government normatividad pages.
    Works with the majority of ministry/agency sites.

    Document URL is None when no specific link is found (instead of using
    the listing page URL, which is misleading).
    """
    soup = BeautifulSoup(html, "lxml")
    docs: list[DocumentResult] = []

    # Remove nav/header/footer noise
    for tag in soup.select("nav, header, footer, .menu, script, style"):
        tag.decompose()

    found_rows = []
    for selector in _SELECTORS:
        found_rows = soup.select(selector)
        if len(found_rows) > 1:
            break

    for row in found_rows:
        title_el = row.select_one("a, .title, h3, h4, td:first-child")
        if not title_el:
            continue

        title = title_el.get_text(separator=" ", strip=True)
        if not title or len(title) < 5:
            continue

        # Get the best possible doc link (may be None)
        doc_url = _best_link(row, base_url)

        doc_type, number = parse_type_number(title)
        pub_date = extract_date_from_text(title + " " + row.get_text())

        docs.append(
            DocumentResult(
                title=title[:300],
                url=doc_url,     # None when no real link found
                doc_type=doc_type or default_doc_type,
                number=number,
                publication_date=pub_date,
                raw_summary=row.get_text(separator=" ", strip=True)[:500],
            )
        )

    # Deduplicate by title+url
    seen: set[tuple] = set()
    result = []
    for d in docs:
        key = (d.title.lower()[:60], d.url)
        if key not in seen and d.is_valid():
            seen.add(key)
            result.append(d)

    return result[:100]


def parse_type_number(title: str) -> tuple[str, str]:
    """Extract document type and number from a norm title."""
    m = re.search(
        r"\b(Ley|Decreto|Resolución|Circular|Acuerdo|Directiva|Auto|Sentencia"
        r"|Providencia|Concepto|Instrucción)\s+([\d\w\-]+)",
        title,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).capitalize(), m.group(2)
    return "", ""


def extract_date_from_text(text: str) -> Optional[date]:
    """Try to extract a publication date from free text."""
    # dd/mm/yyyy or dd-mm-yyyy
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    # yyyy-mm-dd
    m = re.search(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return None
