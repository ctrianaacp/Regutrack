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

8.  **APIs Internas vs Portales Públicos (Bypass de CAPTCHAs y SPAs):**
    *   **El Problema:** Portales como la _Procuraduría General_ usan reCAPTCHA en su frontend. Adicionalmente, SPAs como el _Senado_ pueden bloquear conexiones automáticas (TCP timeouts / WAF) hacia Playwright o Python sin headers, crasheando el proceso del worker.
    *   **La Solución (Ingeniería Inversa):** Siempre examinar el Network/DOM en busca de endpoints puros que alimentan la interfaz o que embeben el contenido.
        *   Para *Procuraduría*: En lugar de resolver el CAPTCHA, se apuntó directamente al endpoint de la relatoría embebido (`https://apps.procuraduria.gov.co/relatoria/index.jsp`) con peticiones `POST` directas.
        *   Para *Senado*: En vez de usar headless browsing que sufría de *TCP Timeout* a nivel local, se extrajo la ruta de la API REST interna (`/api/search_pdly.php`) consumiéndola vía `httpx` empacada como `multipart/form-data`, capturando un fallo limpio (empty list) en caso de sufrir bloqueos por IP para prevenir la caída del scheduler.
        *   Para *Consejo de Estado*: Se escaneó e interceptó el `iframe` oculto que servía los verdaderos datos y no el cascarón frontend.

9.  **Optimización de Contexto de Docker (Importancia del `.dockerignore`):**
    *   **El Error:** `docker compose build api` se quedaba "colgado" durante minutos transfiriendo el build context al demonio de Docker.
    *   **La Causa:** En local, la carpeta `.venv/` de Python (que incluye los pesados binarios del Chromium de Playwright) y las carpetas `node_modules` excedían varios Gigabytes y Docker arrastraba todo por defecto.
    *   **La Solución:** Asegurarse de la existencia estricta de `.dockerignore` en la raíz bloqueando `.venv/`, `frontend/`, `tests/` y `.git/` para compilar la imagen de producción en pocos segundos.

10. **Sincronización de Directorios (Shadow Projects):**
    *   **El Problema:** El scraper o cambio en el código no se refleja en la ejecución (API o Frontend) a pesar de que el archivo existe en el workspace.
    *   **La Causa:** Existen múltiples copias del repositorio en la máquina (ej: `C:\Users\image\ReguTrack` y `C:\Users\image\Proyectos\ReguTrack`). Docker y PM2 pueden estar configurados para apuntar a la ruta antigua, ignorando los cambios en la carpeta de proyectos actual.
    *   **La Solución:** Verificar siempre los puntos de montaje y directorios de trabajo:
        *   Para Docker: `docker inspect regutrack-api --format="{{json .Mounts}}"`
        *   Para PM2: `pm2 describe regutrack-frontend` (buscar `exec cwd`)
        *   Si hay discrepancia, detener los servicios, navegar a la carpeta correcta y ejecutar `docker compose up -d --build` y `pm2 delete ... / pm2 start ...`.

11. **Visibilidad de Títulos en Alertas:**
    *   Los reportes por correo deben priorizar la visibilidad del tema para que el usuario no necesite entrar a la plataforma para entender la relevancia.
    *   **Regla:** No truncar el título del documento en la tabla del correo (`title_str = doc.title`). Usar un tamaño de fuente ligeramente menor (11px) y asegurar que la columna "Tipo" tenga suficiente ancho (140px) para no comprimir el texto.

12. **Evasión de Bloqueos Regionales (Proxy Residencial):**
    *   **El Error:** Al desplegar en producción en un VPS internacional (ej. IONOS), los scrapers hacia `mintrabajo.gov.co`, `sucop.gov.co` y `ansv.gov.co` generaban el error `Timeout 90000ms exceeded`.
    *   **La Causa:** Los WAFs (Firewalls) gubernamentales bloquean o penalizan conexiones que provienen de Datacenters internacionales para evitar ataques DDoS o Scraping agresivo.
    *   **La Solución:** Se implementó soporte de proxies tanto para `Playwright` (`base.py`) como para `httpx` (`http_client.py`). Para evadir la restricción en producción se DEBE comprar una IP de un proxy residencial colombiano (ej. en *Proxy-Cheap* plan *Static Residential ISP*) y configurarla en Coolify mediante la variable de entorno `SCRAPER_PROXY_URL=http://user:pass@ip:puerto`.
    *   **Gotcha de Playwright:** Playwright no acepta nativamente el formato compacto `http://user:pass@ip:puerto` en el parámetro `server`, por lo que el `_fetch_with_playwright` fue refactorizado para parsear la URL usando `urllib.parse.urlparse` y separar el `username` y `password` en el diccionario `proxy_config`.

13. **Errores de Desconexión en ANLA y Entidades Gubernamentales:**
    *   **El Error:** `[Autoridad Nacional de Licencias Ambientales (ANLA)] ✗ Server disconnected without sending a response` o `httpx.ReadTimeout`.
    *   **La Causa:** Frecuentemente los servidores gubernamentales como la Gaceta de la ANLA (`https://gaceta.anla.gov.co:8443`) experimentan caídas totales o cierran puertos aleatoriamente por problemas de infraestructura propia.
    *   **La Solución:** ¡No hacer nada a nivel de código! La arquitectura de `BaseScraper.run` está diseñada para atrapar excepciones como estas sin afectar el resto del ciclo. El orquestador marca el run como `failed`, guarda el error, y reintenta en el próximo cronjob. Es importante verificar si la URL principal está viva (`curl`) antes de intentar debuggear el código del scraper.

14. **Pruebas de Correo Push (Envíos Manuales Retrasados):**
    *   **El Escenario:** A veces quedan correos en cola (`is_new=True`) tras una falla de SMTP o reinicio. Se requiere enviar un correo manual (push) consolidando esos documentos.
    *   **La Solución:** Usar el script `scripts/send_backlog.py` (envía un correo por entidad con intervalos de 15 min). **ESTRICTA REGLA:** Para futuras pruebas de correo push o debug de envío manual, se DEBE modificar temporalmente o asegurar que el `settings.notifier_email_to` apunte **únicamente** a `ctriana@acp.com.co` antes de ejecutar el script. Esto evita inundar de pruebas a toda la lista de gerentes de la ACP.
    *   **Gotcha de Uvicorn `--reload`:** Al inyectar scripts dentro del contenedor con `docker cp`, NUNCA colocarlos dentro de `/app/` ya que Uvicorn detecta el cambio y reinicia el servidor (matando al scheduler y al script). Siempre copiar a `/tmp/` y ejecutar con `docker exec -e PYTHONPATH=/app <container> python3 /tmp/script.py`.

15. **Mismatch de Variables de Entorno SMTP (Nombre del Campo vs Env Var):**
    *   **El Error:** `535 Authentication failed: empty username or password` al intentar enviar correos.
    *   **La Causa:** Coolify define la variable `NOTIFIER_SMTP_PASSWORD`, pero `pydantic-settings` en `config.py` mapeaba al campo `notifier_smtp_pass`, lo cual buscaba la env var `NOTIFIER_SMTP_PASS`. El resultado: la contraseña siempre era un string vacío en producción.
    *   **La Solución:** Renombrar el campo en `config.py` a `notifier_smtp_password` para que coincida exactamente con la variable de Coolify. Adicionalmente, `notifier_email_from` no estaba configurado en Coolify (solo `NOTIFIER_SMTP_USER`), lo que generaba correos con remitente vacío que ElasticEmail descartaba silenciosamente. Se agregó un fallback en `notifier.py`: `sender = settings.notifier_email_from or settings.notifier_smtp_user`.
    *   **Regla:** Al agregar cualquier variable de entorno nueva en Coolify, verificar que el nombre del campo en `config.py` (Pydantic) genere exactamente la misma env var esperada. Pydantic convierte `field_name` → `FIELD_NAME` automáticamente.

16. **Crash del Scheduler por UniqueViolation en ConsejoEstado:**
    *   **El Error:** `psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "uq_entity_hash"` seguido de `PendingRollbackError`.
    *   **La Causa:** El scraper del Consejo de Estado extraía miles de documentos del portal de Biblioteca Digital, y entre ellos venían documentos con el mismo `content_hash` (mismo título + número + URL). Como SQLAlchemy tenía `autoflush=False`, la validación `if existing:` en `_persist_documents` no veía los documentos que acababa de insertar en la misma sesión. Al hacer `flush()` al final, PostgreSQL rechazaba los duplicados, la transacción entera hacía rollback, y **todos** los documentos nuevos de esa entidad se perdían. Al ser la excepción atrapada por `_run_one_scraper`, el scheduler continuaba pero con `result=None` para esa entidad, por lo que sus documentos no llegaban al notificador.
    *   **La Solución:** Se agregó un `set()` local `seen_hashes_this_run` dentro de `_persist_documents()` en `base.py`. Antes de insertar un documento, se verifica si su hash ya fue procesado en el mismo ciclo. Si es duplicado, se ignora silenciosamente.
    *   **Regla:** Nunca confiar en que la base de datos detectará duplicados durante un `flush()` masivo. Siempre implementar deduplicación en memoria antes de persistir.

17. **URLs con Sufijo Aleatorio en MinEnergía (Duplicados Infinitos):**
    *   **El Error:** El scraper de MinEnergía generaba ~13 copias del mismo documento en cada corrida del scheduler (ej. "Decreto 0375" aparecía 13 veces, sumando 140 registros basura en la DB).
    *   **La Causa:** El portal `normativame.minenergia.gov.co` genera URLs de descarga PDF con un número aleatorio al final (ej. `DECRETO_0375_39886.pdf`, `DECRETO_0375_71694.pdf`). Como `compute_hash()` usa `title + number + url`, cada ejecución producía un hash diferente para el mismo documento.
    *   **La Solución:** Se reescribió el scraper para:
        1. Apuntar al portal correcto de normativas (`normativame.minenergia.gov.co`) en vez de la página de Foros/Eventos.
        2. Implementar un hash estable local usando solo `title + number + doc_type` (sin URL) para deduplicación dentro del scraper.
        3. Corregir la URL malformada (`gov.copublic_html` → `gov.co/public_html`).
    *   **Regla:** Cuando un portal gubernamental genera URLs dinámicas/temporales para sus PDFs, el scraper debe usar un hash que **excluya la URL** y se base en campos estables (título, número, tipo). Verificar siempre con `SELECT title, COUNT(*) FROM documents WHERE entity_id=X GROUP BY title HAVING COUNT(*) > 1` si hay duplicados sospechosos.

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
    pm2 restart regutrack-frontend
    ```

## 6. Servidor de Producción (VPS IONOS)

ReguTrack comparte servidor de producción con otros proyectos corporativos a través de Coolify.

*   **IP del Servidor:** `74.208.130.203`
*   **Gestión de Contenedores:** Coolify UI (Puerto 8000).
*   **Acceso SSH Seguro:** 
    *   No se permiten contraseñas, solo autenticación por llave pública (`id_ed25519`).
    *   Comando para acceder (desde la máquina de administración en Windows):
        ```powershell
        ssh -i "$env:USERPROFILE\.ssh\id_ed25519" acpadmin@74.208.130.203
        ```
    *   **NO usar `root`** de forma directa, está bloqueado por seguridad. El usuario `acpadmin` tiene privilegios `sudo`.
*   **Firewall (UFW) y Fail2Ban:** Están activados. **ESTRICTAMENTE PROHIBIDO** abrir puertos de Bases de Datos (`5432`, etc.) al exterior en UFW o Docker (`0.0.0.0`). Las bases de datos en Coolify deben mapearse EXCLUSIVAMENTE a `127.0.0.1`.
*   **Conexión a Bases de Datos (Desarrollo Local):** Los agentes y desarrolladores DEBEN incluir un script/workflow en el proyecto (ej. en `package.json` o un `.bat`) para levantar un Túnel SSH hacia el VPS.
    *   Comando estándar: `ssh -L 5432:localhost:5432 root@74.208.130.203 -N`
    *   Las variables de entorno (`.env`) en desarrollo local siempre deben apuntar a `localhost:5432`.
*   **Estrategia de Despliegue (Coolify):**
    *   El Backend (`Dockerfile.api`) y Frontend (`Next.js / Nixpacks`) se instancian como contenedores independientes dentro del VPS, no usar PM2 en producción.

### Datos de Conexión a la Nueva Infraestructura PostgreSQL (VPS)
*   **Host / IP:** `127.0.0.1` (Puerto `5432` a través de Túnel SSH)
*   **Nombre de la Base de Datos:** `regutrack`
*   **Usuario de la DB:** `postgres`
*   **pgAdmin:** No hay pgAdmin instalado en el VPS. Se debe usar DBeaver o DataGrip localmente mediante la opción de "SSH Tunnel" o levantando el túnel manualmente en la terminal.
