"""Vellum FastAPI application entry point.

Initializes the FastAPI app with lifespan context manager for database setup.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI

from app.database import engine, Base
from app.routes import documents

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Vellum",
    description="Smart Legal Document Manager",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(documents.router)
