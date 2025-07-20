from azure.storage.blob import BlobServiceClient
import os

# Cargar las variables desde el .env
from dotenv import load_dotenv
load_dotenv()

AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "adjuntos")

try:
    print("🔗 Conectando a Azure Blob Storage...")
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_BLOB_CONNECTION_STRING)

    # Obtener cliente del contenedor
    container_client = blob_service_client.get_container_client(AZURE_BLOB_CONTAINER)

    # Comprobar si el contenedor existe
    if not container_client.exists():
        print(f"📦 Contenedor '{AZURE_BLOB_CONTAINER}' no existe. Creándolo...")
        container_client.create_container()
        print(f"✅ Contenedor '{AZURE_BLOB_CONTAINER}' creado.")
    else:
        print(f"📂 Contenedor '{AZURE_BLOB_CONTAINER}' ya existe.")

except Exception as e:
    print(f"❌ Error al conectar con Azure Blob Storage: {e}")

