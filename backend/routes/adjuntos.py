# backend/routes/adjuntos.py
from backend.models.adjunto import Adjunto
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.connection import get_session
from backend.schemas.adjunto import AdjuntoCreate, AdjuntoOut
from datetime import datetime

router = APIRouter(prefix="/api/adjuntos", tags=["adjuntos"])

@router.post("/", response_model=AdjuntoOut)
async def upload_adjunto(
    ticket_id: int = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    # 1. Guardar archivo en Azure Storage (aquí solo simulado)
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    # 2. Registrar en BD
    nuevo = Adjunto(
        ticket_id=ticket_id,
        filename=file.filename,
        url=file_location,  # aquí pones la URL pública real de Azure Storage
        uploaded_at=datetime.utcnow(),
    )
    session.add(nuevo)
    await session.commit()
    await session.refresh(nuevo)
    return nuevo
