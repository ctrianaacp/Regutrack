# ==========================================================================
#  deploy.ps1  –  ReguTrack Persistent Deployment via PM2
#  Usage: .\deploy.ps1
# ==========================================================================

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host ""
Write-Host "══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   ReguTrack — Despliegue con PM2" -ForegroundColor Cyan
Write-Host "══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── 1. Verificar Node.js ───────────────────────────────────────────────────
Write-Host "▶ Verificando Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  ✓ Node.js $nodeVersion encontrado" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Node.js no encontrado. Instálalo desde https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# ── 2. Instalar PM2 si no existe ──────────────────────────────────────────
Write-Host "▶ Verificando PM2..." -ForegroundColor Yellow
$pm2Check = Get-Command pm2 -ErrorAction SilentlyContinue
if (-not $pm2Check) {
    Write-Host "  ⚙ Instalando PM2 globalmente..." -ForegroundColor Yellow
    npm install -g pm2
    Write-Host "  ✓ PM2 instalado" -ForegroundColor Green
} else {
    $pm2Version = pm2 --version 2>&1
    Write-Host "  ✓ PM2 v$pm2Version encontrado" -ForegroundColor Green
}

# ── 3. Verificar entorno Python virtual ───────────────────────────────────
Write-Host "▶ Verificando entorno Python (.venv)..." -ForegroundColor Yellow
$uvicornPath = Join-Path $Root ".venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicornPath)) {
    Write-Host "  ✗ No se encontró .venv\Scripts\uvicorn.exe" -ForegroundColor Red
    Write-Host "    Ejecuta: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✓ uvicorn en .venv encontrado" -ForegroundColor Green

# ── 4. Crear carpeta de logs si no existe ─────────────────────────────────
$logsPath = Join-Path $Root "logs"
if (-not (Test-Path $logsPath)) {
    New-Item -ItemType Directory -Path $logsPath | Out-Null
    Write-Host "  ✓ Carpeta logs/ creada" -ForegroundColor Green
}

# ── 5. Build del frontend ─────────────────────────────────────────────────
Write-Host ""
Write-Host "▶ Construyendo el frontend (next build)..." -ForegroundColor Yellow
Set-Location (Join-Path $Root "frontend")

# Instalar dependencias si node_modules no existe
if (-not (Test-Path "node_modules")) {
    Write-Host "  ⚙ Instalando dependencias npm..." -ForegroundColor Yellow
    npm install
}

npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Build del frontend fallido" -ForegroundColor Red
    Set-Location $Root
    exit 1
}
Write-Host "  ✓ Frontend construido correctamente" -ForegroundColor Green
Set-Location $Root

# ── 6. Detener instancias previas de PM2 (si existen) ────────────────────
Write-Host ""
Write-Host "▶ Deteniendo procesos PM2 anteriores (si los hay)..." -ForegroundColor Yellow
pm2 delete ecosystem.config.js 2>$null
Write-Host "  ✓ Listo" -ForegroundColor Green

# ── 7. Iniciar servicios con PM2 ─────────────────────────────────────────
Write-Host ""
Write-Host "▶ Iniciando servicios con PM2..." -ForegroundColor Yellow
pm2 start ecosystem.config.js

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ PM2 no pudo iniciar los servicios" -ForegroundColor Red
    exit 1
}

# ── 8. Guardar lista de procesos (para sobrevivir reinicios) ──────────────
Write-Host ""
Write-Host "▶ Guardando estado de PM2..." -ForegroundColor Yellow
pm2 save

# ── 9. Configurar startup de Windows ─────────────────────────────────────
Write-Host ""
Write-Host "▶ Configurando inicio automático con Windows..." -ForegroundColor Yellow
Write-Host "  (Puede requerir ejecutar como Administrador en algunos equipos)" -ForegroundColor DarkGray

# PM2 en Windows usa pm2-startup o el WMI startup
# La forma más robusta es usar pm2-windows-startup
$startupCheck = Get-Command pm2-startup -ErrorAction SilentlyContinue
if (-not $startupCheck) {
    Write-Host "  ⚙ Instalando pm2-windows-startup..." -ForegroundColor Yellow
    npm install -g pm2-windows-startup
}
pm2-startup install

Write-Host ""
Write-Host "══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   ✅  ¡Despliegue completado!" -ForegroundColor Green
Write-Host "══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  🌐  Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "  🔌  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  📖  API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "  Comandos útiles de PM2:" -ForegroundColor DarkGray
Write-Host "    pm2 list              — Ver estado de los servicios" -ForegroundColor DarkGray
Write-Host "    pm2 logs              — Ver logs en tiempo real" -ForegroundColor DarkGray
Write-Host "    pm2 restart all       — Reiniciar todos los servicios" -ForegroundColor DarkGray
Write-Host "    pm2 stop all          — Detener todos los servicios" -ForegroundColor DarkGray
Write-Host "    pm2 monit             — Monitor interactivo" -ForegroundColor DarkGray
Write-Host ""
