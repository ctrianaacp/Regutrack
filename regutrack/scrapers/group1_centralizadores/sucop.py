"""SUCOP (Sistema Único de Consulta Pública) scraper.

Scrapes public comment projects for normative documents from various Colombian entities.
"""

from bs4 import BeautifulSoup
from regutrack.scrapers.base import BaseScraper
from regutrack.utils.hashing import DocumentResult
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SUCOPScraper(BaseScraper):
    entity_name = "SUCOP (Consulta Pública)"
    entity_url = "https://www.sucop.gov.co/busqueda"
    entity_group = "group1_centralizadores"
    doc_type_default = "Proyecto de Norma"
    requires_js = True

    async def fetch_documents_with_page(self, page) -> list[DocumentResult]:
        # Navigate and wait for content
        await page.goto(self.entity_url, timeout=90_000, wait_until="domcontentloaded")
        
        # Site is slow and dynamic, wait for the actual results to appear
        try:
            await page.wait_for_selector(".bq-proceso", timeout=60_000)
        except Exception:
            # If nothing found, it might be an empty search
            pass
            
        # Give it a small extra buffer for all items to render
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        return self._parse_sucop_html(html)

    def _parse_sucop_html(self, html: str) -> list[DocumentResult]:
        soup = BeautifulSoup(html, "lxml")
        docs = []
        
        # Based on debug HTML, items are in .bq-proceso
        items = soup.select(".bq-proceso")
        for item in items:
            # 1. Title and Link
            title_el = item.select_one(".normaTitle a")
            if not title_el:
                continue
                
            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            if link and not link.startswith("http"):
                link = "https://www.sucop.gov.co" + (link if link.startswith("/") else "/" + link)

            # 2. Entity
            entity_el = item.select_one(".bq-col-entidad .font-weight-bold")
            entity_text = entity_el.get_text(strip=True) if entity_el else ""
            
            # Combine entity with title
            full_title = f"[{entity_text}] {title}" if entity_text else title

            # 3. Dates
            pub_date = None
            pub_date_el = item.select_one(".bq-col-publicado .bq-fechas-value")
            if pub_date_el:
                pub_date = self._parse_date(pub_date_el.get_text(strip=True))

            # 4. Description / Summary
            desc_el = item.select_one(".bq-resultado-description")
            summary = desc_el.get_text(strip=True) if desc_el else ""
            
            # Additional metadata for summary
            status_el = item.select_one(".activa, .cerrada, .finalizada")
            status = status_el.get_text(strip=True) if status_el else ""
            
            sector_el = item.select_one(".bq-col-sector .font-weight-bold")
            sector = sector_el.get_text(strip=True) if sector_el else ""
            
            extended_summary = f"Estado: {status} | Sector: {sector}\n{summary}"

            docs.append(
                DocumentResult(
                    title=full_title[:500],
                    url=link,
                    doc_type=self.doc_type_default,
                    publication_date=pub_date,
                    raw_summary=extended_summary[:1000]
                )
            )
            
        return docs

    def _parse_date(self, date_str: str):
        """Parse date in format d/m/yyyy."""
        try:
            # Try common format
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        except Exception:
            # Fallback to general regex extraction
            import re
            m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str)
            if m:
                try:
                    from datetime import date
                    return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                except ValueError:
                    return None
        return None
