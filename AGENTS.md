# ReguTrack - Contexto para Agentes y LLMs

Este archivo contiene el contexto general, arquitectura, stack tecnológico y reglas de negocio de **ReguTrack**, una plataforma diseñada para monitorear, extraer (scrapear) y alertar sobre cambios normativos de diversas entidades gubernamentales en Colombia.

## 1. Stack Tecnológico

*   **Backend:** Python 3.11+, FastAPI, SQLAlchemy (ORM), APScheduler (tareas en segundo plano).
*   **Base de Datos:** PostgreSQL (en producción vía Docker), SQLite (`regutrack.db`, fallback local).
*   **Web Scraping:** Playwright (para páginas dinámicas/JS) y `httpx` / `BeautifulSoup` (para sitios simples).
*   **Frontend:** Next.js 14, React, TypeScript.
*   **Infraestructura & Despliegue (Windows):**
    *   **Backend & DB:** Docker Compose (`api` y `db`).
    *   **Frontend:** PM2 (`ecosystem.config.js`).

## 2. Arquitectura General del Sistema

El flujo general de ReguTrack es el siguiente:
1.  **Scraping Programado / Manual:** Los scrapers extraen normativas de sitios como la ANE, DIAN, SIC, etc.
2.  **Base de Datos:** Se guarda un registro de la entidad (`Entity`), los documentos encontrados (`Document`), y el historial de ejecuciones (`ScrapeRun`).
3.  **Filtrado:** Si un documento ya existe (por URL, título o número), se marca como actualizado. Si es nuevo, se marca con `is_new=True`.
4.  **Notificaciones:** Al finalizar una ejecución (ya sea por el *scheduler* o manualmente), el sistema recolecta los documentos marcados como nuevos y envía un correo consolidado (y opcionalmente, un webhook).

### 2.1 Componentes del Backend (`/api` y `/regutrack`)

*   **`api/main.py`**: El punto de entrada de FastAPI. En el ciclo de vida (startup/shutdown), inicializa la base de datos y arranca el **scheduler** de tareas, de forma que los procesos automáticos empiecen a correr apenas inicie el contenedor.
*   **`api/routers/`**:
    *   `/entities`: Devuelve la lista de entidades, estadísticas y permite ejecutar un scraper manualmente (`POST /api/run/{key}`). Devuelve la `key` exacta configurada en el backend.
    *   `/documents`: Lista los documentos scrapeados, permitiendo filtros y paginación.
    *   `/runs`: Historial de ejecuciones (`ScrapeRun`), estado (success, failed, partial), y errores.
*   **`regutrack/scrapers/`**: Todos los scrapers heredan de la clase base. Cada entidad (ej. `ANEScraper`) tiene su propia implementación especializada. Existe un diccionario global `SCRAPERS_BY_KEY` que mapea un identificador único (ej. `"ane"`) con la clase correspondiente.
*   **`regutrack/scheduler.py`**: Maneja `APScheduler`. Está configurado a través de variables de entorno para correr periódicamente cada `SCHEDULER_INTERVAL_HOURS` (por defecto 6), sincronizándose la primera vez con la hora `SCHEDULER_HOUR:SCHEDULER_MINUTE`.
*   **`regutrack/notifier.py`**: Lógica de alertas. Se encarga de formatear el template HTML y enviar el email a través de SMTP (ElasticEmail). Envía un reporte únicamente si se hallaron documentos nuevos.

### 2.2 Componentes del Frontend (`/frontend`)

*   **Proxy de API:** Next.js está configurado (`next.config.js`) para redirigir las peticiones que empiecen con `/api/*` hacia el backend (por defecto `http://localhost:8000`).
*   **Cliente API (`src/lib/api.ts`)**: Define las entidades de TS y contiene todas las llamadas fetch preconfiguradas agrupadas por `entities`, `documents`, `runs` y `stats`.
*   **Componentes Principales**: 
    *   `Dashboard` (`page.tsx`): KPIs, últimas ejecuciones y un gráfico resumen.
    *   `EntitiesPage` (`entities/page.tsx`): Tabla de entidades donde permite detonar un scrape en demanda usando la `key` del backend, evitando deducirla por nombre.

## 3. Lecciones Aprendidas (Gotchas y Bugs Resueltos)

Si estás modificando código, **evita estos problemas conocidos**:

1.  **Conflicto de Event Loops (Playwright en FastAPI y Scheduler):**
    *   **El Error:** `<asyncio.locks.Lock object ... > is bound to a different event loop`.
    *   **La Causa:** `asyncio.run()` dentro de un hilo de APScheduler o `BackgroundTasks` de FastAPI comparte los locks internos de Playwright con el loop de Uvicorn. Si múltiples scrapers se disparan juntos bajo el mismo loop, los locks de Playwright quedan "atados" al primer loop y fallan en el siguiente.
    *   **La Solución:** Cada scraper (tanto en el scheduler como en el endpoint manual) debe correr en su **propio event loop aislado** usando el patrón:
    *   *Código seguro — aplicado en `scheduler.py` (`_run_one_scraper`) y `entities.py` (`_run_scraper_bg`)*:
        ```python
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(scraper.run(session))
        finally:
            loop.close()
        ```
    *   **NUNCA usar** `asyncio.run(_run_all_async())` para correr múltiples scrapers consecutivos en el mismo hilo — esto fue lo que causó el fallo masivo del scheduler (63 de 75 scrapers fallando simultáneamente el 2026-03-25).

2.  **Identificadores de Entidades (Key Mismatch):**
    *   **El Error:** Frontend manda a buscar la entidad `a_n_e` y recibe HTTP 404 porque la key real es `ane`. Esto solía ocurrir porque el frontend intentaba generar inteligentemente el nombre en snake_case interpretando las mayúsculas (ej: `ANEScraper` -> `a_n_e`).
    *   **La Solución:** El backend envía un campo `key` en el `EntitySchema` mapeando su nombre registrado en el diccionario `SCRAPERS_BY_KEY`. El frontend siempre debe enviarle el parámetro `/api/run/${entity.key}` para detonar un scrape manual, sin transformación alguna del string.

3.  **PM2 en Windows:**
    *   **El Error:** Los puertos se quedan en uso tras reiniciar, o la aplicación Next.js no inicia, o el backend intenta ser administrado doble y choca con el puerto 8000 de Docker.
    *   **La Causa:** Entorno Windows con shells como Git Bash o PowerShell tienen problemas con los `.cmd` bajo `interpreter: "none"`. Además, gestionar backend Dockerizado con PM2 causa puertos zombie en 0.0.0.0.
    *   **La Solución:** El framework PM2 solo maneja el **frontend** en `ecosystem.config.js`. Usar `interpreter: "node"` apuntando directamente al binario transpilado JS `node_modules/next/dist/bin/next` para Windows en lugar del script `npm`.

4.  **Integración de Scheduler en FastAPI:**
    *   Múltiples runs manuales no deben cruzar o detener el loop de `APScheduler`. En el ciclo de vida de la aplicación (`lifespan()`), instanciar globalmente el schedule con el método `scheduler.start()` y desmontar al terminar con `scheduler.shutdown(wait=False)`.

5.  **Notificaciones API vs Scheduler:**
    *   Ambos métodos (el scheduler automatizado y el `POST /api/run/*` manual) importan y llaman al terminarse la función `notify_run_summary()`. Anteriormente, el gatillo local/manual olvidaba llamar al notificador, impidiendo enviar el e-mail a pesar de que hubiera documentos recientes.

6.  **URLs de Destino para Scrapers (Targeting Normatividad):**
    *   **El Error:** Scrapers como la ANI extraían basura (menús, links a "Transparencia") que ensuciaban el reporte y base de datos.
    *   **La Causa:** La clase definía `entity_url = f"{_BASE}/"`. El parser estándar de HTML buscaba tablas y terminaba atrapando contenedores genéricos de la página de inicio.
    *   **La Solución:** Todo Web Scraper de esta aplicación **debe** apuntar directamente a sub-páginas formales de emisión de normas (ej. `/normativa/normograma`, `/informacion-de-la-ani/normatividad`, o sus portales *Gaceta*), NUNCA al root domain, para que el fallo en caso de no hallar normas sea resultar en `0 documentos` en lugar de generar falsos positivos.

7.  **Timeout en Scrapers Playwright (`networkidle` vs `domcontentloaded`):**
    *   **El Error:** `Page.goto: Timeout 45000ms exceeded` en scrapers como ANE, UPME, MinVivienda y MinMinas.
    *   **La Causa:** `wait_until="networkidle"` espera que no haya peticiones de red por 500ms. Los sitios modernos (SharePoint Online, WordPress/Elementor, Drupal Views, React SPAs) tienen peticiones continuas (analytics, heartbeats, websockets) que **nunca** permiten alcanzar `networkidle`.
    *   **La Solución:** Usar `wait_until="domcontentloaded"` (solo espera que el HTML esté parseado) + `wait_for_selector("<selector_del_contenido>")` para confirmar que el contenido relevante cargó. Aumentar el timeout a 60–90s para sitios lentos.
    *   *Patrón correcto:*
        ```python
        await page.goto(url, timeout=90_000, wait_until="domcontentloaded")
        await page.wait_for_selector("div.mi-contenido", timeout=30_000)
        ```
    *   **Scrapers afectados y corregidos:** `ane.py` (60s), `upme.py` (90s, 3 URLs), `minvivienda.py` (90s), `minenergia.py` (90s).

## 4. Archivo .env
Las configuraciones críticas están aquí. Las principales relacionadas con el core de la app son:
*   `VITE_API_URL` / `NEXT_PUBLIC_API_URL`: Definientes de la API proxy (típicamente de cliente).
*   `SCHEDULER_HOUR`, `SCHEDULER_MINUTE`, `SCHEDULER_INTERVAL_HOURS`: Define el punto cronólogico exacto para el loop del cron (América/Bogotá).
    *   Ejemplo: Si está a las 17:30 e intervalo de 6h, disparará 17:30, 23:30, 05:30, 11:30.
*   Credenciales SMTP (`NOTIFIER_SMTP_HOST`, `NOTIFIER_SMTP_USER`, `NOTIFIER_SMTP_PASSWORD`, `NOTIFIER_EMAIL_TO`).
*   Database y OpenAI (Usado de fallback por algunos scrapers más complejos como en MinJusticia/SUIN).

## 5. Repositorio y Control de Versiones

*   **Repositorio GitHub:** [`ctrianaacp/Regutrack`](https://github.com/ctrianaacp/Regutrack)
*   **Rama principal:** `master`
*   **`.gitignore` excluye:** `.env`, `.venv/`, `*.db`, `frontend/node_modules/`, `frontend/package-lock.json`, `frontend/.next/`, scripts de debug temporales.
*   **Flujo de trabajo para subir cambios:**
    ```powershell
    git add .
    git commit -m "tipo: descripción del cambio"
    git push
    ```
*   **Rebuild del backend tras cambios en Python:**
    ```powershell
    docker compose build api
    docker compose up -d api
    ```
*   **Rebuild del frontend tras cambios en Next.js:**
    ```powershell
    cd frontend; npm run build; cd ..
    pm2 restart regutrack-frontend
    ```
