"""FastAPI application — ReguTrack REST API."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import entities, documents, runs, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables and start background scheduler on startup."""
    from regutrack.database import init_db
    from regutrack.scheduler import create_scheduler
    init_db()
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="ReguTrack API",
    description="Sistema de monitoreo normativo colombiano — REST API",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Next.js frontend (dev: 3000, prod: configurable)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(stats.router, prefix="/api")
app.include_router(entities.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(runs.router, prefix="/api")


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "ReguTrack API"}
