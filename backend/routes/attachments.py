from fastapi import APIRouter, File, UploadFile, HTTPException
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import os
import uuid
from datetime import datetime, timedelta
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.connection import get_session
from backend.database.models import Attachment
from sqlalchemy import select

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

@router.post("/{ticket_id}/attachments")
async def upload_attachment(ticket_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_session)):
    """
    Sube el archivo a Azure Blob y registra en la base de datos.
    """
    extension = os.path.splitext(file.filename)[1]
    blob_name = f"{ticket_id}/{uuid.uuid4()}{extension}"

    try:
        # Sube el archivo a Azure Blob Storage
        blob_client = container_client.get_blob_client(blob_name)
        content = await file.read()
        blob_client.upload_blob(content, overwrite=True)

        # Guarda referencia en DB con el nombre de blob
        new_attachment = Attachment(
            ticket_id=ticket_id,
            filename=file.filename,
            file_url=blob_name  # Guardamos solo el blob_name para generar SAS después
        )
        db.add(new_attachment)
        await db.commit()

        return {"message": "Archivo subido correctamente", "name": file.filename}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error subiendo archivo: {e}")

@router.get("/{ticket_id}/attachments")
async def list_attachments(ticket_id: int, db: AsyncSession = Depends(get_session)):
    """
    Devuelve la lista de archivos adjuntos con URLs temporales SAS.
    """
    try:
        result = await db.execute(
            select(Attachment).where(Attachment.ticket_id == ticket_id)
        )
        attachments = result.scalars().all()

        if attachments:
            return [
                {
                    "name": att.filename,
                    "url": generate_sas_url(att.file_url)
                }
                for att in attachments
            ]
        else:
            # Fallback: blobs directos desde Azure con SAS
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
