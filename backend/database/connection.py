"""
Database connection setup for SQLAlchemy and PostgreSQL.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from backend.config.settings import get_settings
from typing import AsyncGenerator

# Obtén la URL de la base de datos desde tu archivo de configuración
DATABASE_URL = get_settings().DATABASE_URL

# Crea el engine asíncrono de SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Crea la fábrica de sesiones asíncronas
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initialize database (placeholder)."""
    # Si necesitas lógica de inicialización, agrégala aquí
    pass

# Dependency para inyección de sesión en FastAPI (lo usas en los endpoints)
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

# Utilidad para consumir sesión fuera de los endpoints (como en background tasks)
async def get_db_session() -> AsyncSession:
    """
    Devuelve una sesión asíncrona lista para usarse fuera de Depends (por ejemplo, en background).
    Debes cerrarla manualmente con await session.close()
    """
    async_gen = get_session()
    session = await anext(async_gen)
    return session


