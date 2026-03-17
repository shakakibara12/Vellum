"""Database configuration for Vellum application.

Provides async SQLAlchemy engine setup with aiosqlite driver for SQLite.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./vellum.db"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """Base class for all SQLAlchemy models."""


async def get_db() -> AsyncSession:
    """Dependency to get async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
