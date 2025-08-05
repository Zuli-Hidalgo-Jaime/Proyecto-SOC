# scripts/create_admin_user.py

import asyncio
from backend.database.connection import get_db_session, engine
from backend.database.models import User
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin_user():
    async with engine.begin():
        session = await get_db_session()
        username = "zuli"
        password = "contrasena"
        hashed_password = pwd_context.hash(password)
        user = User(
            username=username,
            password_hash=hashed_password,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.commit()
        print(f"✅ Usuario '{username}' creado correctamente.")

if __name__ == "__main__":
    asyncio.run(create_admin_user())

