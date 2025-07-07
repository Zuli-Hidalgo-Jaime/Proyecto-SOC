import asyncio
from backend.config.settings import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_connection():
    db_url = get_settings().DATABASE_URL
    print(f"Intentando conectar a: {db_url}")

    engine = create_async_engine(db_url, echo=True)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar_one()
            print(f"Conexión exitosa. Versión de PostgreSQL: {version}")
    except Exception as e:
        print(f"Fallo la conexión: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())
