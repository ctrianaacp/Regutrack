import asyncio
import logging

from regutrack.scrapers.group3_control.procuraduria import ProcuradoriaScraper
from regutrack.scrapers.group2_ministerios.mintrabajo import MintrabajuScraper
from regutrack.scrapers.group2_ministerios.minhacienda import MinhaciendaScraper
from regutrack.scrapers.group1_centralizadores.sucop import SUCOPScraper

logging.basicConfig(level=logging.INFO)

async def test_scraper(name, cls):
    print(f"\n--- Probando {name} ---")
    scraper = cls()
    try:
        docs = await scraper._safe_fetch()
        print(f"Éxito: {len(docs)} documentos encontrados.")
        for d in docs[:3]:
            print(f" - {d.title}")
    except Exception as e:
        print(f"Error en {name}: {e}")

async def main():
    await test_scraper("Procuraduría (SSL)", ProcuradoriaScraper)
    await test_scraper("MinHacienda (Playwright 403)", MinhaciendaScraper)
    await test_scraper("MinTrabajo (Playwright Timeout)", MintrabajuScraper)
    await test_scraper("SUCOP (Playwright Lento)", SUCOPScraper)

if __name__ == "__main__":
    asyncio.run(main())
