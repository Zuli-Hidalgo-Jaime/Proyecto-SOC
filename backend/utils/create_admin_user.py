import asyncio
from backend.database.connection import engine, get_db_session
from backend.database.models import User
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin_user():
    async with engine.begin() as conn:
        session = await get_db_session()
        username = "zuli"
        password = "contrasena"

        # Hashear contraseña
        hashed_password = pwd_context.hash(password)

        # Crear usuario
        user = User(
            username=username,
            password_hash=hashed_password,
            created_at=datetime.utcnow()
        )

        session.add(user)
        await session.commit()
        print(f"✅ Usuario '{username}' creado correctamente.")

asyncio.run(create_admin_user())
