#backend/database/connection.py
"""
Database connection setup for SQLAlchemy and PostgreSQL.
Provee utilidades para crear sesiones y engine asíncronos.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from backend.config.settings import get_settings
from typing import AsyncGenerator

DATABASE_URL = get_settings().DATABASE_URL

# Engine asíncrono de SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Fábrica de sesiones asíncronas
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Inicializa la base de datos si se requiere lógica adicional."""
    pass

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency para inyección de sesión en FastAPI.
    Uso: session: AsyncSession = Depends(get_session)
    """
    async with SessionLocal() as session:
        yield session

async def get_db_session() -> AsyncSession:
    """
    Devuelve una sesión asíncrona lista para usarse fuera de Depends (por ejemplo, en background).
    Debes cerrarla manualmente con await session.close()
    """
    async_gen = get_session()
    session = await anext(async_gen)
    return session
