"""ANSV — Agencia Nacional de Seguridad Vial scraper.

The normativa page is a Drupal Views page that renders documents as
cards.  Each card has:
  - Type badge (Resolución, Circular, etc.)
  - Number
  - Expedition date
  - Title text
  - "Ver documento" link to the PDF
  - "Ver contenido" link to the detail page

The page is server-rendered but the card structure is NOT a standard
<table>, so parse_standard_normatividad_page fails to extract anything.
We use Playwright to reliably get the fully-rendered HTML and then
parse the card list items.
"""
import re
from datetime import date

from bs4 import BeautifulSoup

from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult

_BASE = "https://ansv.gov.co"
_URL = f"{_BASE}/es/normativa"


class ANSVScraper(BaseScraper):
    entity_name = "Agencia Nacional de Seguridad Vial (ANSV)"
    entity_url = _URL
    entity_group = "group5_agencias"
    doc_type_default = "Resolución ANSV"
    requires_js = True

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        await page.goto(_URL, timeout=90_000, wait_until="domcontentloaded")
        # Wait for the normativa listing cards to render
        try:
            await page.wait_for_selector(
                "a[href*='Ver documento'], a[href*='/sites/default/files/']",
                timeout=30_000,
            )
        except Exception:
            pass  # Fall through and try parsing whatever we got
        await page.wait_for_timeout(2_000)

        html = await page.content()
        return self._parse_cards(html)

    def _parse_cards(self, html: str) -> list[DocumentResult]:
        soup = BeautifulSoup(html, "lxml")
        docs: list[DocumentResult] = []
        seen: set[str] = set()

        # Each normativa item is an <li> inside the views listing
        items = soup.select("ul.content-list > li, div.view-content li, .views-row")
        if not items:
            # Fallback: just find all "Ver documento" links
            items = [soup]

        for item in items:
            # Find "Ver documento" link (PDF)
            doc_link = item.find("a", string=re.compile(r"Ver documento", re.I))
            if not doc_link:
                # Try href pattern
                doc_link = item.find("a", href=re.compile(
                    r"/sites/default/files/.*\.(pdf|xlsx?|docx?)", re.I
                ))
            if not doc_link:
                continue

            href = doc_link.get("href", "")
            if not href:
                continue
            url = href if href.startswith("http") else f"{_BASE}{href}"
            if url in seen:
                continue
            seen.add(url)

            # Extract title from surrounding text
            title = self._extract_title(item)
            if not title or len(title) < 5:
                # Use filename as fallback
                title = href.split("/")[-1].replace("_", " ").replace(".pdf", "")

            doc_type, number = self._extract_type_number(item)

            pub_date = self._extract_date(item)

            docs.append(
                DocumentResult(
                    title=title[:300],
                    url=url,
                    doc_type=doc_type or self.doc_type_default,
                    number=number,
                    publication_date=pub_date,
                )
            )

        return docs

    @staticmethod
    def _extract_title(item) -> str:
        """Get the best title from the card item."""
        # Look for a content link or prominent text
        content_link = item.find("a", string=re.compile(r"Ver contenido", re.I))
        if content_link:
            # The title is usually the text before the links section
            # Walk backwards from the content link
            pass

        # Get the full text and try to find the longest meaningful line
        all_text = item.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in all_text.split("\n") if l.strip()]

        # Filter out button/nav text
        skip = {"Ver documento", "Ver contenido", "Resolución", "Circular",
                "Decreto", "Ley", "Acuerdo", "Concepto", "Normograma"}
        meaningful = []
        for line in lines:
            if line in skip or len(line) < 10:
                continue
            if re.match(r"^de \d{2}/\d{2}/\d{4}$", line):
                continue
            if re.match(r"^\d{2}/\d{2}/\d{4}$", line):
                continue
            if re.match(r"^\d+$", line):
                continue
            meaningful.append(line)

        if meaningful:
            return meaningful[0]
        return ""

    @staticmethod
    def _extract_type_number(item) -> tuple[str, str]:
        """Extract doc type (Resolución, Circular, etc.) and number."""
        text = item.get_text(separator=" ", strip=True)
        m = re.search(
            r"\b(Resolución|Circular|Decreto|Ley|Acuerdo|Concepto|Normograma)\s+(\d+)",
            text, re.I,
        )
        if m:
            return m.group(1).capitalize(), m.group(2)
        # Type without number
        m2 = re.search(
            r"\b(Resolución|Circular|Decreto|Ley|Acuerdo|Concepto|Normograma)\b",
            text, re.I,
        )
        if m2:
            return m2.group(1).capitalize(), ""
        return "", ""

    @staticmethod
    def _extract_date(item) -> date | None:
        """Extract publication/expedition date from card text."""
        text = item.get_text(separator=" ", strip=True)
        m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if m:
            try:
                return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                pass
        return None
