from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database import engine, Base
from app.models import Document, DocumentVersion  # noqa: F401 - Import models to register them


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


@app.get("/")
async def root():
    """Root endpoint returning API status."""
    return {"status": "ok"}
