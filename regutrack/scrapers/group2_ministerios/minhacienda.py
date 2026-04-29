"""Ministerio de Hacienda scraper.

The MinHacienda portal is behind a Radware WAF/CDN that blocks
automated HTTP requests (returns 403 Forbidden to httpx/requests).
Must use Playwright to bypass the bot protection.

The Oracle WebCenter page loads normativa via JavaScript so we need
a headless browser regardless.
"""
import re
from datetime import date

from bs4 import BeautifulSoup

from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult

_BASE = "https://www.minhacienda.gov.co"
_URL = (
    f"{_BASE}/webcenter/portal/MHweb/"
    "pages_MH_NormatividadYDocumentacion/PageMH_NormatividadDocumentacion"
)


class MinhaciendaScraper(BaseScraper):
    entity_name = "Ministerio de Hacienda"
    entity_url = _URL
    entity_group = "group2_ministerios"
    doc_type_default = "Norma Hacienda"
    requires_js = True  # Radware WAF blocks plain HTTP; Oracle WebCenter needs JS

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        await page.goto(_URL, timeout=90_000, wait_until="domcontentloaded")

        # Wait for the WebCenter content panel to load
        try:
            await page.wait_for_selector(
                "table, .AFDetached, a[href*='.pdf'], a[href*='decreto'], "
                "a[href*='resoluci'], .panelFormLayout",
                timeout=30_000,
            )
        except Exception:
            pass  # Parse whatever rendered

        await page.wait_for_timeout(3_000)

        html = await page.content()
        return self._parse(html)

    def _parse(self, html: str) -> list[DocumentResult]:
        soup = BeautifulSoup(html, "lxml")
        docs: list[DocumentResult] = []
        seen: set[str] = set()

        # Remove nav/footer noise
        for tag in soup.select("nav, header, footer, .menu, script, style"):
            tag.decompose()

        # Strategy 1: Find all links that point to normative docs
        norm_pattern = re.compile(
            r"(decreto|resoluci[oó]n|circular|ley|acuerdo|directiva|norma|"
            r"documento|archivo|anexo|\.pdf|\.doc)",
            re.IGNORECASE,
        )

        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            text = a.get_text(strip=True)

            if not href or href.startswith(("javascript:", "#", "mailto:")):
                continue

            # Must match normative keyword in href or text
            if not norm_pattern.search(href) and not norm_pattern.search(text):
                continue

            # Skip navigation-style links
            if len(text) < 5:
                continue

            url = href if href.startswith("http") else f"{_BASE}{href}"
            if url in seen:
                continue
            seen.add(url)

            doc_type, number = self._type_number(text)
            pub_date = self._extract_date(text)

            docs.append(
                DocumentResult(
                    title=text[:300],
                    url=url,
                    doc_type=doc_type or self.doc_type_default,
                    number=number,
                    publication_date=pub_date,
                )
            )

        # Strategy 2: If strategy 1 yielded nothing, try table rows
        if not docs:
            from regutrack.scrapers.common import parse_standard_normatividad_page
            docs = parse_standard_normatividad_page(html, _BASE, self.doc_type_default)

        return docs[:100]

    @staticmethod
    def _type_number(title: str) -> tuple[str, str]:
        m = re.search(
            r"\b(Ley|Decreto|Resolución|Circular|Acuerdo|Directiva)\s+([\d\w\-]+)",
            title, re.IGNORECASE,
        )
        if m:
            return m.group(1).capitalize(), m.group(2)
        return "", ""

    @staticmethod
    def _extract_date(text: str) -> date | None:
        m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if m:
            try:
                return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                pass
        return None
