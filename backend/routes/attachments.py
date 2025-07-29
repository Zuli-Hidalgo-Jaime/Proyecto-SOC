#backend/routes/attachments.py
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import select as sa_select
from datetime import datetime, timedelta
import os
import uuid

from backend.database.connection import get_session
from backend.database.models import Attachment, Ticket
from backend.embeddings.service import embed_and_store
from backend.utils.ocr import extract_ocr

router = APIRouter(prefix="/api/tickets")

# Lee de .env o settings.py
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
            expiry=datetime.utcnow() + timedelta(minutes=30)  # URL válida por 30 min
        )
        return f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_BLOB_CONTAINER}/{blob_name}?{sas_token}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando SAS URL: {e}")


# ✅ ESTA RUTA VA PRIMERO para evitar conflictos con /{ticket_id}
@router.get("/{ticket_id}/attachments")
async def list_attachments(ticket_id: int, db: AsyncSession = Depends(get_session)):
    """
    Devuelve la lista de archivos adjuntos con URLs temporales SAS.
    Si un blob ya no existe en Azure, lo borra de la base de datos.
    """
    try:
        # Buscar adjuntos en la base de datos
        result = await db.execute(
            select(Attachment).where(Attachment.ticket_id == ticket_id)
        )
        attachments = result.scalars().all()

        cleaned_attachments = []  # Guardamos los que sí existen en Azure

        for att in attachments:
            blob_client = container_client.get_blob_client(att.file_url)
            if blob_client.exists():
                # Si el blob existe en Azure, lo agregamos a la lista
                cleaned_attachments.append({
                    "id": att.id,  # Incluimos el ID para eliminar desde frontend
                    "name": att.filename,
                    "url": generate_sas_url(att.file_url)
                })
            else:
                # Si el blob NO existe en Azure, lo borramos de la DB
                await db.delete(att)
                await db.commit()

        if cleaned_attachments:
            return cleaned_attachments
        else:
            # Si no hay nada en DB o todo fue eliminado, listar blobs directos de Azure
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
    # --- VALIDACIÓN DE EXTENSIÓN ---
    allowed_ext = {".png", ".jpg", ".jpeg", ".pdf"}
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in allowed_ext:
        raise HTTPException(
            status_code=415,
            detail=f"Formato no permitido: '{extension}'. Solo se aceptan: PNG, JPG, JPEG, PDF."
        )

    blob_name = f"{ticket_id}/{uuid.uuid4()}{extension}"

    try:
        # Sube el archivo a Azure Blob Storage
        blob_client = container_client.get_blob_client(blob_name)
        content = await file.read()
        blob_client.upload_blob(content, overwrite=True)

        # Extrae OCR del archivo
        ocr_text = extract_ocr(content, file.filename)

        # Guarda referencia en DB, incluyendo el texto OCR
        new_attachment = Attachment(
            ticket_id=ticket_id,
            filename=file.filename,
            file_url=blob_name,
            ocr_content=ocr_text
        )
        db.add(new_attachment)
        await db.commit()

        # --------- REGENERA EMBEDDING ---------
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
        import traceback
        print("⛔️ Error en upload_attachment:", repr(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error subiendo archivo: {e}")

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error subiendo archivo: {e}")

@router.delete("/{ticket_id}/attachments/{attachment_id}")
async def delete_attachment(ticket_id: int, attachment_id: int, db: AsyncSession = Depends(get_session)):
    try:
        # Buscar el adjunto en DB
        result = await db.execute(
            select(Attachment).where(
                Attachment.id == attachment_id,
                Attachment.ticket_id == ticket_id
            )
        )
        attachment = result.scalars().first()

        if not attachment:
            raise HTTPException(status_code=404, detail="Adjunto no encontrado en la base de datos")

        # Eliminar del blob
        blob_client = container_client.get_blob_client(attachment.file_url)
        blob_client.delete_blob()

        # Eliminar de DB
        await db.delete(attachment)
        await db.commit()

        # --------- REGENERA EMBEDDING ---------
        # 1. Obtener el ticket
        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if ticket:
            # 2. Obtener todos los attachments restantes del ticket (con su OCR)
            result2 = await db.execute(select(Attachment).where(Attachment.ticket_id == ticket_id))
            attachments = result2.scalars().all()
            ocr_texts = [att.ocr_content for att in attachments if att.ocr_content]

            # 3. Unir los campos del ticket y todos los OCR para el embedding
            ticket_dict = ticket.__dict__.copy()
            ticket_dict["attachments_ocr"] = ocr_texts

            await embed_and_store(
                key=f"ticket:{ticket.id}",
                ticket=ticket_dict,
                ticket_id=ticket.id,
                status=ticket.Status
            )
        # --------------------------------------

        return {"message": "Archivo eliminado correctamente"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando archivo: {e}")
