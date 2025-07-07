# backend/database/test_pg_connection.py

import pytest
from backend.config.settings import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

pytestmark = pytest.mark.asyncio  # <-- Esto indica que los tests del archivo son async

async def test_connection():
    db_url = get_settings().DATABASE_URL
    assert db_url is not None, "DATABASE_URL no está definido en el entorno"
    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar_one()
            print(f"Conexión exitosa. Versión de PostgreSQL: {version}")
            assert "PostgreSQL" in version
    finally:
        await engine.dispose()
