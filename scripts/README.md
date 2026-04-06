# Scripts de Utilidad — ReguTrack

Scripts de apoyo para desarrollo, debugging y mantenimiento. **No son parte del core de la aplicación.**

| Script | Propósito |
|---|---|
| `run_scraper.py` | Correr un scraper manualmente desde consola |
| `debug_scraper.py` | Inspeccionar el comportamiento de un scraper |
| `real_scrape_test.py` | Prueba de scraping real contra sitios en vivo |
| `real_scrape_test2.py` | Segunda variante de prueba de scraping real |
| `check_db.py` | Inspeccionar el estado de la base de datos local |
| `cleanup_ane.py` | Limpiar registros duplicados de ANE en la DB |
| `fix_emails.py` | Corregir campos de email en la DB |
| `verify_ai.py` | Verificar que la integración con OpenAI funciona |

> Todos estos scripts deben correrse desde la raíz del proyecto con el `.venv` activo:
> ```powershell
> .\.venv\Scripts\Activate.ps1
> python scripts\run_scraper.py
> ```
