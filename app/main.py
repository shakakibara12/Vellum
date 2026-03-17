from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.database import engine, Base
from app.models import Document, DocumentVersion  # noqa: F401 - Import models to register them
from app.routes import documents

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: Cleanup if needed
    await engine.dispose()


app = FastAPI(
    title="Vellum",
    description="Smart Legal Document Manager",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(documents.router)


@app.get("/health")
async def health():
    """Health check endpoint returning API status."""
    return {"status": "ok"}
