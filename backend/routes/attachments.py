#backend/routes/attachments.py
"""
Rutas para gestión de archivos adjuntos en tickets.
Incluye: listar, subir y eliminar archivos en Azure Blob Storage con integración OCR y embeddings.
"""

import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database.connection import get_session
from backend.database.models import Attachment, Ticket
from backend.embeddings.service import embed_and_store
from backend.utils.ocr import extract_ocr

router = APIRouter(prefix="/api/tickets")

AZURE_BLOB_CONN_STR = os.getenv("AZURE_BLOB_CONNECTION_STRING")
AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "ticket-attachments")
blob_service_client = BlobServiceClient.from_connection_string(AZURE_BLOB_CONN_STR)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)

def generate_sas_url(blob_name: str) -> str:
    """
    Genera una URL con SAS (Shared Access Signature) para acceder al blob de forma segura.
    """
    try:
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=AZURE_BLOB_CONTAINER,
            blob_name=blob_name,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=30)
        )
        return f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_BLOB_CONTAINER}/{blob_name}?{sas_token}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando SAS URL: {e}")

@router.get("/{ticket_id}/attachments")
async def list_attachments(ticket_id: int, db: AsyncSession = Depends(get_session)):
    """
    Devuelve la lista de archivos adjuntos con URLs temporales SAS.
    Si un blob ya no existe en Azure, lo borra de la base de datos.
    """
    try:
        result = await db.execute(select(Attachment).where(Attachment.ticket_id == ticket_id))
        attachments = result.scalars().all()

        cleaned_attachments = []

        for att in attachments:
            blob_client = container_client.get_blob_client(att.file_url)
            if blob_client.exists():
                cleaned_attachments.append({
                    "id": att.id,
                    "name": att.filename,
                    "url": generate_sas_url(att.file_url)
                })
            else:
                await db.delete(att)
                await db.commit()

        if cleaned_attachments:
            return cleaned_attachments
        else:
            blobs = container_client.list_blobs(name_starts_with=f"{ticket_id}/")
            return [
                {
                    "name": blob.name.split("/")[-1],
                    "url": generate_sas_url(blob.name)
                }
                for blob in blobs
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar archivos: {e}")

@router.post("/{ticket_id}/attachments")
async def upload_attachment(ticket_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_session)):
    """
    Sube un archivo a Azure Blob Storage, extrae su OCR, guarda referencia en DB y regenera embedding.
    """
    allowed_ext = {".png", ".jpg", ".jpeg", ".pdf"}
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in allowed_ext:
        raise HTTPException(
            status_code=415,
            detail=f"Formato no permitido: '{extension}'. Solo se aceptan: PNG, JPG, JPEG, PDF."
        )

    blob_name = f"{ticket_id}/{uuid.uuid4()}{extension}"

    try:
        blob_client = container_client.get_blob_client(blob_name)
        content = await file.read()
        blob_client.upload_blob(content, overwrite=True)

        ocr_text = extract_ocr(content, file.filename)

        new_attachment = Attachment(
            ticket_id=ticket_id,
            filename=file.filename,
            file_url=blob_name,
            ocr_content=ocr_text
        )
        db.add(new_attachment)
        await db.commit()

        # Regenera embeddings con todos los OCR actuales
        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if ticket:
            result2 = await db.execute(select(Attachment).where(Attachment.ticket_id == ticket_id))
            attachments = result2.scalars().all()
            ocr_texts = [att.ocr_content for att in attachments if att.ocr_content]
            ticket_dict = ticket.__dict__.copy()
            ticket_dict["attachments_ocr"] = ocr_texts

            await embed_and_store(
                key=f"ticket:{ticket.id}",
                ticket=ticket_dict,
                ticket_id=ticket.id,
                status=ticket.Status
            )
        return {"message": "Archivo subido correctamente", "name": file.filename}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error subiendo archivo: {e}")

@router.delete("/{ticket_id}/attachments/{attachment_id}")
async def delete_attachment(ticket_id: int, attachment_id: int, db: AsyncSession = Depends(get_session)):
    """
    Elimina un archivo adjunto del ticket, borra del storage, de la DB y regenera embedding.
    """
    try:
        result = await db.execute(
            select(Attachment).where(
                Attachment.id == attachment_id,
                Attachment.ticket_id == ticket_id
            )
        )
        attachment = result.scalars().first()

        if not attachment:
            raise HTTPException(status_code=404, detail="Adjunto no encontrado en la base de datos")

        blob_client = container_client.get_blob_client(attachment.file_url)
        blob_client.delete_blob()

        await db.delete(attachment)
        await db.commit()

        # Regenera embeddings
        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if ticket:
            result2 = await db.execute(select(Attachment).where(Attachment.ticket_id == ticket_id))
            attachments = result2.scalars().all()
            ocr_texts = [att.ocr_content for att in attachments if att.ocr_content]
            ticket_dict = ticket.__dict__.copy()
            ticket_dict["attachments_ocr"] = ocr_texts

            await embed_and_store(
                key=f"ticket:{ticket.id}",
                ticket=ticket_dict,
                ticket_id=ticket.id,
                status=ticket.Status
            )

        return {"message": "Archivo eliminado correctamente"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando archivo: {e}")
