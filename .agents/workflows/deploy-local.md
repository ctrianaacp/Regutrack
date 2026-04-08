---
description: despliegue completo de ReguTrack en local (Docker + PM2)
---

# Despliegue Local de ReguTrack

Este workflow levanta el stack completo de ReguTrack en Windows:
- **Backend**: Docker Compose (PostgreSQL + FastAPI en puertos 5432/8000)
- **Frontend**: Next.js compilado y servido por PM2 (puerto 3000)

## Prerrequisitos

- Docker Desktop corriendo
- Node.js instalado
- PM2 instalado globalmente (`npm install -g pm2`)

---

## Opción A: Script único (recomendado)

// turbo
1. Ejecutar el script de despliegue completo desde la raíz del proyecto:
```powershell
.\start-local.ps1
```

**Parámetros disponibles:**
- `.\start-local.ps1 -SkipBuild` — Omite `npm run build` (usa el `.next/` ya compilado)
- `.\start-local.ps1 -Stop` — Detiene Docker y PM2

---

## Opción B: Paso a paso

### 1. Levantar Backend (Docker)
// turbo
```powershell
docker compose up -d
```
Esperar a que el API responda en http://localhost:8000/health.

### 2. Build del Frontend
// turbo
```powershell
cd frontend
npm run build
cd ..
```

### 3. Iniciar/Reiniciar Frontend con PM2
// turbo
```powershell
pm2 start ecosystem.config.js
```
O si ya estaba corriendo:
```powershell
pm2 restart regutrack-frontend
```

---

## Verificar el despliegue

// turbo
```powershell
# Estado de contenedores Docker
docker compose ps

# Estado de PM2
pm2 status

# Probar API
curl.exe -s http://localhost:8000/api/stats

# Probar Frontend (proxy → API)
curl.exe -s http://localhost:3000/api/stats
```

**URLs de acceso:**
- 🌐 Frontend: http://localhost:3000
- 🔌 Backend: http://localhost:8000
- 📖 API Docs: http://localhost:8000/docs
- 🐘 pgAdmin: http://localhost:5050

---

## Troubleshooting

### Frontend no muestra datos
El problema más común es que el contenedor `regutrack-api` todavía está iniciando.
1. Revisar logs: `docker logs regutrack-api --tail 50`
2. Si muestra `Application startup complete` → esperar y refrescar el browser
3. Si muestra error de conexión a DB → reiniciar: `docker restart regutrack-api`

### Puerto 3000 ocupado
```powershell
# Encontrar proceso usando el puerto
netstat -ano | findstr :3000
# Matar proceso (reemplazar PID)
taskkill /PID <PID> /F
```

### Rebuild completo del backend
```powershell
docker compose build api
docker compose up -d api
```

### Logs en tiempo real
```powershell
# Backend
docker logs regutrack-api -f
# Frontend  
pm2 logs regutrack-frontend
```
