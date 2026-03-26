# ReguTrack

> Sistema de monitoreo y trazabilidad de publicación de normas, resoluciones y decretos expedidos por entidades del Estado colombiano.

## ¿Qué hace?

- Ejecuta scrapers diarios contra ~30 portales gubernamentales
- Detecta documentos nuevos o modificados (leyes, decretos, resoluciones, circulares, sentencias)
- Almacena hallazgos en base de datos con historial de cambios
- Alerta sobre novedades mediante logs y webhooks opcionales

## Instalación

```bash
# 1. Clonar / abrir la carpeta del proyecto
cd ReguTrack

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Instalar Playwright (navegador headless para sitios JS)
playwright install chromium

# 5. Configurar variables de entorno
copy .env.example .env
# Editar .env según necesidad

# 6. Inicializar base de datos
python -m regutrack.cli db init
```

## Uso (CLI)

```bash
# Ejecutar todos los scrapers ahora
python -m regutrack.cli run-all

# Ejecutar un scraper específico
python -m regutrack.cli run --entity anh
python -m regutrack.cli run --entity imprenta_nacional

# Ver documentos nuevos de los últimos N días
python -m regutrack.cli show-new --days 7

# Iniciar el scheduler (corre diariamente a las 06:00 hora Colombia)
python -m regutrack.cli scheduler start

# Reinicializar la base de datos (cuidado: borra datos)
python -m regutrack.cli db init --reset
```

## Entidades Monitoreadas

### Grupo 1 — Grandes Centralizadores
| Entidad | URL |
|---|---|
| SUIN-Juriscol (MinJusticia) | suin-juriscol.gov.co |
| Imprenta Nacional (Diario Oficial) | imprenta.gov.co |
| Gestor Normativo (Función Pública) | funcionpublica.gov.co |
| Secretaría Jurídica Distrital | sincronia.alcaldiabogota.gov.co |

### Grupo 2 — Ministerios y Presidencia
| Entidad | URL |
|---|---|
| Presidencia de la República | dapre.presidencia.gov.co |
| Ministerio de Hacienda | minhacienda.gov.co |
| Ministerio de Salud | minsalud.gov.co |
| Ministerio de Educación | mineducacion.gov.co |
| Ministerio de Minas y Energía | minenergia.gov.co |
| MinTIC | mintic.gov.co |
| Ministerio de Transporte | mintransporte.gov.co |

### Grupo 3 — Organismos de Control
| Entidad | URL |
|---|---|
| Superintendencia de Industria (SIC) | buscadoractos.sic.gov.co |
| Superfinanciera | superfinanciera.gov.co |
| DIAN | dian.gov.co |
| Contraloría General | contraloria.gov.co |
| Procuraduría General | procuraduria.gov.co |

### Grupo 4 — Rama Legislativa y Judicial
| Entidad | URL |
|---|---|
| Senado de la República | senado.gov.co |
| Corte Constitucional | corteconstitucional.gov.co |
| Consejo de Estado | consejodeestado.gov.co |

### Grupo 5 — Agencias Nacionales
| Entidad | Sigla | URL |
|---|---|---|
| Agencia Nacional de Hidrocarburos | ANH | anh.gov.co |
| Agencia Nacional de Tierras | ANT | ant.gov.co |
| Agencia Nacional de Licencias Ambientales | ANLA | anla.gov.co |
| Agencia Nacional de Infraestructura | ANI | ani.gov.co |
| Agencia Nacional de Minería | ANM | anm.gov.co |
| Agencia Nacional de Seguridad Vial | ANSV | ansv.gov.co |
| Agencia Nacional del Espectro | ANE | ane.gov.co |

### Grupo 6 — Entidades Descentralizadas
| Entidad | URL |
|---|---|
| Aeronáutica Civil | aerocivil.gov.co |
| INVÍAS | invias.gov.co |
| DNP | dnp.gov.co |
| DANE | dane.gov.co |
| ICBF | icbf.gov.co |

## Estructura del Proyecto

```
ReguTrack/
├── regutrack/
│   ├── config.py          # Configuración con pydantic-settings
│   ├── database.py        # Motor SQLAlchemy
│   ├── models.py          # Modelos ORM
│   ├── scheduler.py       # Jobs diarios con APScheduler
│   ├── cli.py             # Interfaz de línea de comandos
│   ├── notifier.py        # Sistema de alertas
│   ├── scrapers/
│   │   ├── base.py        # Clase base abstracta
│   │   ├── group1_centralizadores/
│   │   ├── group2_ministerios/
│   │   ├── group3_control/
│   │   ├── group4_legislativa/
│   │   ├── group5_agencias/
│   │   └── group6_descentralizadas/
│   └── utils/
│       ├── http_client.py # Cliente HTTP con reintentos
│       └── hashing.py     # Detección de cambios
├── alembic/               # Migraciones de DB
├── logs/                  # Logs de ejecución
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

## Notas

- Los scrapers son **no invasivos**: respetan delays entre requests y User-Agent apropiados.
- Sitios con renderizado JS usan **Playwright** (Chromium headless).
- Si un portal falla, el scraper registra el error y continúa con los demás.
- Base de datos: **SQLite** (desarrollo) / **PostgreSQL** (producción).
