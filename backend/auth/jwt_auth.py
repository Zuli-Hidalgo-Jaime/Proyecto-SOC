# backend/routes/auth.py
"""
Auth básico con JWT (login/registro) para el Proyecto SOC.

- SECRET_KEY y expiración se leen desde variables de entorno (con fallback).
- Mantiene los mismos endpoints y lógica.
"""

import os
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext  # (no se usa directamente, se mantiene por compat)

from backend.database.connection import get_session
from backend.database.models import User
from backend.auth.hash_utils import hash_password, verify_password

# ==== CONFIGURACIÓN ====
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "un_secreto_ultra_secreto")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))

router = APIRouter(prefix="/api/auth")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class UserRegister(BaseModel):
    """
    Modelo para registro de usuario.
    """
    username: str
    password: str
    full_name: str
    email: EmailStr
    role: str = "user"


@router.post("/register")
async def register(user: UserRegister, db: AsyncSession = Depends(get_session)):
    """
    Registra un nuevo usuario si el username no existe.
    """
    result = await db.execute(select(User).where(User.username == user.username))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Usuario ya existe")

    new_user = User(
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        password_hash=hash_password(user.password),
        role=user.role,
        created_at=datetime.utcnow(),
    )
    db.add(new_user)
    await db.commit()
    return {"msg": "Usuario registrado"}


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_session),
):
    """
    Autentica y devuelve un access token JWT (tipo bearer).
    """
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
    }


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Genera un JWT firmado con SECRET_KEY.

    Args:
        data: Claims base (ej. sub, role).
        expires_delta: Duración opcional. Si no se especifica, usa ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Token JWT en formato compacto.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Decodifica el JWT y retorna el usuario actual (username, role).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        role: str | None = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return {"username": username, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


