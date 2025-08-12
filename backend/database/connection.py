# backend/database/connection.py
"""
Database connection setup for SQLAlchemy (async) with PostgreSQL.
Provee utilidades para crear el engine y sesiones asíncronas.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.config.settings import get_settings

DATABASE_URL = get_settings().DATABASE_URL

# Engine asíncrono de SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Fábrica de sesiones asíncronas
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """
    Hook de inicialización de base de datos.
    Útil si necesitas correr migraciones o seed inicial.
    """
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia para inyección de sesión en FastAPI.
    Uso:
        async def endpoint(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with SessionLocal() as session:
        yield session


async def get_db_session() -> AsyncSession:
    """
    Obtiene una sesión asíncrona fuera de Depends (p.ej. en tareas en background).
    NOTA: Debes cerrarla manualmente con:
        await session.close()
    """
    async_gen = get_session()
    session = await anext(async_gen)
    return session
