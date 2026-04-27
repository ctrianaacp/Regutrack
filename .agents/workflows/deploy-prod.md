# Despliegue en Producción de ReguTrack (IONOS + Coolify)

Este flujo de trabajo documenta el proceso estandarizado para actualizar o desplegar desde cero la plataforma **ReguTrack** en el servidor VPS de producción (IONOS) administrado a través de **Coolify**.

## 1. Preparación del Repositorio (Paso Local)

Coolify automatiza los despliegues escuchando los cambios en GitHub. Antes de realizar cualquier acción en el servidor, asegúrate de que tu código local esté estable.

```powershell
// turbo
git add .
git commit -m "chore: preparación para despliegue en producción"
git push origin master
```

> [!IMPORTANT]
> Recuerda que la rama principal del proyecto está configurada como `master` (no `main`).

## 2. Acceso a la Infraestructura

1. Ingresa a la interfaz de administración de Coolify: `http://74.208.130.203:8000`
2. Si requieres validaciones internas por terminal, conéctate por SSH al VPS:
   `ssh -i "$env:USERPROFILE\.ssh\id_ed25519" acpadmin@74.208.130.203`

## 3. Configuración de Base de Datos PostgreSQL (Si es desde cero)

1. En Coolify, crea un recurso **Database -> PostgreSQL**.
2. **Settings**:
   * **Database Name**: `regutrack`
   * **User**: `postgres`
3. **Network (Mapeo de Puertos)**:
   * **Ports Mappings**: `5433:5432` *(Usamos 5433 externamente porque el 5432 original ya está en uso por otro proyecto del VPS).*
4. Guarda los cambios y haz clic en **Start**. Coolify generará una **URL interna** (ej: `postgres://...l11f...:5432/postgres`) necesaria para el Backend.

## 4. Despliegue del Backend (FastAPI + Playwright)

1. Crea una nueva aplicación: **+ Add Resource -> Application -> Public Repository**.
2. Selecciona `ctrianaacp/Regutrack` y la rama `master`.
3. **Configuración de Build:**
   * **Build Pack**: `Docker`
   * **Base Directory**: `/` *(Es crucial que sea la raíz para que Docker tenga el contexto completo de las carpetas).*
   * **Dockerfile Location**: `/Dockerfile.api`
4. **Configuración de Red (Network):**
   * **Ports Exposes**: `8000`
   * **Network Aliases**: `regutrack-api` *(Fundamental para que el Frontend lo encuentre).*
5. **Variables de Entorno (.env):**
   * `DATABASE_URL`: Pegar la URL interna de la BD asegurándote de que inicie con **`postgresql://`** (y NO `postgres://` para evitar fallos de SQLAlchemy).
   * `OPENAI_API_KEY`, `NOTIFIER_SMTP_*`, y `SCHEDULER_INTERVAL_HOURS`.
6. Haz clic en **Deploy**.

## 5. Despliegue del Frontend (Next.js)

1. Crea una nueva aplicación en el mismo entorno de Coolify apuntando al mismo repositorio y rama `master`.
2. **Configuración General:**
   * **Domains**: `https://regutrack.acp.com.co`
3. **Configuración de Build:**
   * **Build Pack**: `Nixpacks` *(Recomendado por defecto para Next.js).*
   * **Base Directory**: `/frontend`
4. **Variables de Entorno (.env):**
   * No es necesario definir `NEXT_PUBLIC_API_URL` para que el proxy interno funcione correctamente con rutas relativas, evitando así errores de **Mixed Content (HTTPS vs HTTP)** en el navegador. Las configuraciones del código (`api.ts` y `next.config.js`) ya manejan el enrutamiento interno de `/api/*` hacia el alias del backend automáticamente.
5. Haz clic en **Deploy**.

## 6. Resolución de Problemas Comunes

* **El backend se apaga (crashea) al inicio:** Verifica la variable `DATABASE_URL`. Si Coolify generó `postgres://`, cámbialo a `postgresql://`.
* **El Frontend no carga datos (Error 500/ECONNREFUSED):** Verifica que el **Network Alias** del backend esté escrito correctamente (ej. `regutrack-api`) y que el contenedor del backend esté en estado *Healthy*.
* **Mixed Content en consola del navegador:** Asegúrate de que el Frontend no tenga inyectada una URL HTTP pública en el `.env`. Las peticiones del cliente deben ser relativas (`/api/stats`), y Next.js hará el proxy seguro en el servidor de fondo.
