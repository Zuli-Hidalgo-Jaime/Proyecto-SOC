# backend/routes/attachments.py

from fastapi import APIRouter, File, UploadFile, HTTPException
from azure.storage.blob import BlobServiceClient
import os
import uuid

router = APIRouter(prefix="/api/tickets")

# Lee de .env o settings.py
AZURE_BLOB_CONN_STR = os.getenv("AZURE_BLOB_CONNECTION_STRING")
AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "ticket-attachments")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_BLOB_CONN_STR)
container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)

@router.post("/{ticket_id}/attachments")
async def upload_attachment(ticket_id: int, file: UploadFile = File(...)):
    # Crea un nombre único (puedes personalizar la estructura de carpetas)
    extension = os.path.splitext(file.filename)[1]
    blob_name = f"{ticket_id}/{uuid.uuid4()}{extension}"

    try:
        # Sube el archivo a Azure Blob Storage
        blob_client = container_client.get_blob_client(blob_name)
        content = await file.read()
        blob_client.upload_blob(content, overwrite=True)
        # URL de descarga pública o SAS, depende de config de tu blob
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_BLOB_CONTAINER}/{blob_name}"
        # Aquí puedes guardar en la base de datos la referencia si lo deseas
        return {"message": "Archivo subido correctamente", "blob_url": blob_url, "name": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo archivo: {e}")
