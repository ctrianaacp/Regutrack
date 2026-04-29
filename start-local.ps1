# ==========================================================================
#  start-local.ps1  –  ReguTrack: Despliegue completo en local (un solo comando)
#
#  Levanta:
#    1. Túnel SSH       → Conexión a PostgreSQL en VPS (puerto 5432)
#    2. Docker Compose  → FastAPI (puerto 8000)
#    3. Next.js build   → Compila el frontend de producción
#    4. PM2             → Sirve el frontend (puerto 3000)
#
#  Uso:
#    .\start-local.ps1            # Despliegue completo
#    .\start-local.ps1 -SkipBuild # Omite npm build (usa .next anterior)
#    .\start-local.ps1 -Stop      # Detiene todo
# ==========================================================================

param(
    [switch]$SkipBuild,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition

function Write-Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "  [X] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "==================================================" -ForegroundColor Magenta
Write-Host "   ReguTrack - Despliegue Local Completo"          -ForegroundColor Magenta
Write-Host "==================================================" -ForegroundColor Magenta

# ------------------------------------------------------------------------------
# MODO STOP: detener todo
# ------------------------------------------------------------------------------
if ($Stop) {
    Write-Step "Deteniendo servicios..."

    pm2 delete ecosystem.config.js 2>$null
    Write-OK "PM2: frontend detenido"

    Set-Location $Root
    docker compose down 2>$null
    Write-OK "Docker: contenedores detenidos"

    # Detener túnel SSH en puerto 5432
    $sshPids = Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
    if ($sshPids) {
        $sshPids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
        Write-OK "Túnel SSH: detenido"
    }

    Write-Host "`n  STOP  Todos los servicios detenidos.`n" -ForegroundColor Yellow
    exit 0
}

# ------------------------------------------------------------------------------
# PASO 1: Verificar dependencias
# ------------------------------------------------------------------------------
Write-Step "Verificando dependencias..."

# Docker
try {
    $dockerVersion = docker --version 2>&1
    Write-OK "Docker: $dockerVersion"
} catch {
    Write-Fail "Docker no está instalado o no está corriendo. Inicia Docker Desktop."
    exit 1
}

# Docker Compose
try {
    docker compose version 2>&1 | Out-Null
    Write-OK "Docker Compose: disponible"
} catch {
    Write-Fail "Docker Compose no disponible."
    exit 1
}

# Node.js
try {
    $nodeVer = node --version 2>&1
    Write-OK "Node.js: $nodeVer"
} catch {
    Write-Fail "Node.js no encontrado. Instálalo desde https://nodejs.org/"
    exit 1
}

# PM2
$pm2Exists = Get-Command pm2 -ErrorAction SilentlyContinue
if (-not $pm2Exists) {
    Write-Warn "PM2 no encontrado. Instalando..."
    npm install -g pm2
    Write-OK "PM2 instalado"
} else {
    Write-OK "PM2: $(pm2 --version 2>&1)"
}

# ------------------------------------------------------------------------------
# PASO 2: Crear carpeta de logs
# ------------------------------------------------------------------------------
$logsPath = Join-Path $Root "logs"
if (-not (Test-Path $logsPath)) {
    New-Item -ItemType Directory -Path $logsPath | Out-Null
    Write-OK "Carpeta logs/ creada"
}

# ------------------------------------------------------------------------------
# PASO 3: Levantar Túnel SSH y Backend (FastAPI)
# ------------------------------------------------------------------------------
Write-Step "Levantando Túnel SSH hacia VPS de producción..."
# Verificar si el puerto 5432 ya está en uso
$portInUse = Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue
if (-not $portInUse) {
    Start-Process -NoNewWindow -FilePath "ssh" -ArgumentList "-i $env:USERPROFILE\.ssh\id_ed25519 -L 5432:127.0.0.1:5432 acpadmin@74.208.130.203 -N"
    Write-OK "Túnel SSH: iniciado en background"
    Start-Sleep -Seconds 3
} else {
    Write-OK "Túnel SSH: ya hay un servicio escuchando en el puerto 5432"
}

Write-Step "Levantando backend con Docker Compose..."
Set-Location $Root

docker compose up -d --build api
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Docker Compose falló. Revisa los logs con: docker compose logs api"
    exit 1
}
Write-OK "Contenedor iniciado (FastAPI)"

# ------------------------------------------------------------------------------
# PASO 4: Esperar a que el API esté listo (hasta 60 seg)
# ------------------------------------------------------------------------------
Write-Step "Esperando a que el backend esté listo..."
$maxWait = 60
$waited = 0
$apiReady = $false

while ($waited -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 3 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $apiReady = $true
            break
        }
    } catch { }

    Start-Sleep -Seconds 3
    $waited += 3
    Write-Host "  ... esperando API ($waited/$maxWait seg)" -ForegroundColor DarkGray
}

if (-not $apiReady) {
    Write-Warn "El API no respondió en $maxWait seg. Puede que aún esté iniciando."
    Write-Warn "Continúa el proceso igualmente. Verifica con: docker logs regutrack-api"
} else {
    Write-OK "API respondiendo en http://localhost:8000/health"
}

# ------------------------------------------------------------------------------
# PASO 5: Build del frontend (Next.js)
# ------------------------------------------------------------------------------
$frontendPath = Join-Path $Root "frontend"
Set-Location $frontendPath

if (-not $SkipBuild) {
    Write-Step "Construyendo el frontend (npm run build)..."

    # Instalar dependencias si no existen
    if (-not (Test-Path "node_modules")) {
        Write-Warn "node_modules no encontrado. Instalando..."
        npm install
    }

    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Build del frontend falló."
        Set-Location $Root
        exit 1
    }
    Write-OK "Frontend compilado correctamente"
} else {
    Write-Warn "Omitiendo build del frontend (--SkipBuild activo)"
}

Set-Location $Root

# ------------------------------------------------------------------------------
# PASO 6: Reiniciar PM2 (frontend)
# ------------------------------------------------------------------------------
Write-Step "Iniciando/reiniciando frontend con PM2..."

# Si ya existe el proceso, reiniciarlo; si no, crear nuevo
$pm2List = pm2 list 2>&1
if ($pm2List -match "regutrack-frontend") {
    pm2 restart regutrack-frontend
    Write-OK "PM2: proceso 'regutrack-frontend' reiniciado"
} else {
    pm2 start ecosystem.config.js
    Write-OK "PM2: proceso 'regutrack-frontend' iniciado"
}

pm2 save 2>$null

# ------------------------------------------------------------------------------
# PASO 7: Verificar estado final
# ------------------------------------------------------------------------------
Write-Step "Verificando estado final..."
Start-Sleep -Seconds 3

# Verificar frontend
try {
    $fe = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 5 -ErrorAction Stop
    Write-OK "Frontend accesible en http://localhost:3000 (HTTP $($fe.StatusCode))"
} catch {
    Write-Warn "Frontend aún no responde en http://localhost:3000 — espera unos segundos"
}

# Verificar API
try {
    $api = Invoke-WebRequest -Uri "http://localhost:8000/api/stats" -TimeoutSec 5 -ErrorAction Stop
    Write-OK "Backend accesible en http://localhost:8000/api/stats"
} catch {
    Write-Warn "Backend no respondió — verifica: docker logs regutrack-api"
}

# ------------------------------------------------------------------------------
# RESUMEN FINAL
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "  OK  ReguTrack desplegado correctamente!"        -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  🌐  Frontend:   http://localhost:3000"            -ForegroundColor White
Write-Host "  🔌  Backend:    http://localhost:8000"            -ForegroundColor White
Write-Host "  📖  API Docs:   http://localhost:8000/docs"       -ForegroundColor White
Write-Host ""
Write-Host "  Comandos útiles:" -ForegroundColor DarkGray
Write-Host "    pm2 logs regutrack-frontend  — Logs del frontend en tiempo real" -ForegroundColor DarkGray
Write-Host "    docker logs regutrack-api -f — Logs del backend en tiempo real"  -ForegroundColor DarkGray
Write-Host "    docker compose ps            — Estado de contenedores Docker"    -ForegroundColor DarkGray
Write-Host "    .\start-local.ps1 -Stop      — Detener todo"                    -ForegroundColor DarkGray
Write-Host ""
