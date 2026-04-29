---
name: deploy-local
description: Despliega ReguTrack completamente en local (Docker + PM2 + Next.js build). Útil cuando el usuario dice "levanta la app", "despliega en local", o "el front/backend no funciona".
---

# Skill: Despliegue Local de ReguTrack

## Cuándo usar este skill

Úsalo cuando el usuario pida:
- Desplegar, levantar, iniciar o reiniciar la aplicación en local
- El frontend no muestra datos
- El backend no responde
- "Levanta el front", "levanta todo", "reinicia los servicios"

---

## Arquitectura de despliegue

```
Windows (local)
│
├── Docker Compose           ← Maneja: API
│   └── regutrack-api        (FastAPI + Uvicorn, puerto 8000)
│
├── Túnel SSH                ← Conexión a Base de Datos
│   └── Puerto 5432 local -> VPS Producción (74.208.130.203)
│
└── PM2                      ← Maneja: Solo el frontend
    └── regutrack-frontend   (Next.js build, puerto 3000)
```

**IMPORTANTE:** PM2 gestiona ÚNICAMENTE el frontend. El backend va vía Docker y la BD usa un túnel SSH.

---

## Pasos de despliegue completo

### Paso 1 — Levantar Túnel SSH y Docker (API)

Primero inicia el túnel SSH hacia la BD de producción:
```powershell
Start-Process -NoNewWindow ssh -ArgumentList "-i $env:USERPROFILE\.ssh\id_ed25519 -L 5432:127.0.0.1:5432 acpadmin@74.208.130.203 -N"
```

Luego arranca el contenedor de la API:
```powershell
# Desde la raíz del proyecto
docker compose up -d api
```

Verifica que los contenedores están saludables:
```powershell
docker compose ps
```
Espera output como:
```
regutrack-api    Up
```

Si `regutrack-api` aparece como `Exited`, reinícialo (puede que la DB no estaba lista):
```powershell
docker restart regutrack-api
```

Espera hasta que el API responda:
```powershell
# Verificar que el API está vivo
curl.exe -s http://localhost:8000/health
# Respuesta esperada: {"status":"ok","service":"ReguTrack API"}
```

### Paso 2 — Compilar el frontend

```powershell
cd frontend
npm run build
cd ..
```

Espera que termine sin errores. Debe terminar con "Route (app)" en la salida.

### Paso 3 — Levantar frontend con PM2

```powershell
# Si ya existe el proceso PM2
pm2 restart regutrack-frontend

# Si es primera vez o fue eliminado
pm2 start ecosystem.config.js

# Guardar estado de PM2
pm2 save
```

### Paso 4 — Verificar despliegue completo

```powershell
# API respondiendo
curl.exe -s http://localhost:8000/api/stats

# Proxy frontend → API (debe retornar el mismo JSON)
curl.exe -s http://localhost:3000/api/stats

# Estado de PM2
pm2 status
```

---

## Script de un solo comando

Existe un script que automatiza todos los pasos anteriores:

```powershell
# Despliegue completo (build incluido)
.\start-local.ps1

# Despliegue rápido (skip del build si .next/ ya existe)
.\start-local.ps1 -SkipBuild

# Detener todo
.\start-local.ps1 -Stop
```

---

## Diagnóstico cuando los datos no aparecen en el frontend

La causa más común es que el frontend hace fetch a `/api/*`, que Next.js redirige a `http://localhost:8000/api/*`. Si el contenedor de la API no está up, las peticiones fallan silenciosamente en el cliente.

**Checklist de diagnóstico:**

1. ¿Están los contenedores corriendo?
   ```powershell
   docker ps
   ```

2. ¿La API responde?
   ```powershell
   curl.exe -s http://localhost:8000/health
   ```

3. ¿El proxy de Next.js funciona?
   ```powershell
   curl.exe -s http://localhost:3000/api/stats
   ```

4. ¿El contenedor API tuvo errores?
   ```powershell
   docker logs regutrack-api --tail 50
   ```

5. ¿El frontend tiene errores?
   ```powershell
   pm2 logs regutrack-frontend --lines 50
   ```

### Error frecuente: API exitosa pero con error de DB

```
sqlalchemy.exc.OperationalError: FATAL: the database system is starting up
```
**Solución:** El contenedor API arrancó antes de que PostgreSQL estuviera listo.
```powershell
docker restart regutrack-api
# Esperar ~10 segundos y verificar
curl.exe -s http://localhost:8000/health
```

---

## URls del sistema local

| Servicio | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
