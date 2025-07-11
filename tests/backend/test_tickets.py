# tests/backend/test_tickets.py
import asyncio, pytest
from backend.config.settings import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


@pytest.mark.asyncio
async def test_connection():
    db_url = get_settings().DATABASE_URL
    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            version = (await conn.execute(text("SELECT version();"))).scalar_one()
            assert "PostgreSQL" in version
    finally:
        await engine.dispose()

