"""
Database connection setup for SQLAlchemy and PostgreSQL.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from backend.config.settings import get_settings
from contextlib import asynccontextmanager  # <-- Añade esto

# TODO: Use asyncpg for async PostgreSQL
DATABASE_URL = get_settings().DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Initialize database (placeholder)."""
    # TODO: Implement database initialization logic
    pass

# ---- Dependency para FastAPI ----
async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
