# Backend - API FastAPI

Esta carpeta contiene la API REST para la gestión de tickets, con integración a PostgreSQL y Redis para embeddings. Aquí solo está la base, debes completar la lógica siguiendo los TODOs y docstrings.

## Estructura

- `main.py`: Aplicación principal FastAPI.
- `models/`: Modelos Pydantic y SQLAlchemy.
- `routes/`: Endpoints de la API.
- `services/`: Lógica de negocio.
- `database/`: Configuración de base de datos.
- `embeddings/`: Módulo de embeddings con Azure OpenAI y Redis.
- `config/`: Configuración de la aplicación.
- `utils/`: Utilidades (por ejemplo, cliente Redis).

## Pasos para trabajar en el backend

1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Crea un archivo `.env` en la raíz con las variables de entorno necesarias (ver ejemplo en este README).
3. Completa los modelos, rutas y servicios siguiendo los TODOs y docstrings en cada archivo.
4. Asegúrate de que la API funcione localmente y pueda conectarse a PostgreSQL y Redis.
5. Usa la documentación automática en `/docs` para probar los endpoints.
6. Si necesitas agregar lógica para embeddings, revisa la carpeta `embeddings/` y la integración con Redis.

## Variables de entorno requeridas

```
DATABASE_URL=postgresql://usuario:contraseña@localhost/proyectosoc
AZURE_OPENAI_ENDPOINT=https://tu-recurso.openai.azure.com/
AZURE_OPENAI_API_KEY=tu-api-key
AZURE_REDIS_CONNECTION_STRING=tu-redis-connection-string
AZURE_STORAGE_CONNECTION_STRING=tu-storage-connection-string
```

## Consejos

- Trabaja por módulos: termina y prueba cada parte antes de pasar a la siguiente.
- Usa los TODOs y docstrings como guía para saber qué falta implementar.
- Haz pruebas con `pytest` y revisa los ejemplos en la carpeta `tests/`.
- Consulta la documentación oficial de FastAPI, SQLAlchemy y Redis si tienes dudas.
- Si tienes problemas, pregunta a tu mentor/a.

## Características

- API REST completa para CRUD de tickets
- Integración con PostgreSQL
- Generación de embeddings con Azure OpenAI
- Almacenamiento de vectores en Azure Redis Enterprise
- Soporte para archivos adjuntos (Azure Blob Storage)
- Documentación automática con Swagger/OpenAPI

## Ejecución

```bash
# Desarrollo
uvicorn main:app --reload

# Producción
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /api/tickets` - Listar tickets
- `POST /api/tickets` - Crear ticket
- `GET /api/tickets/{id}` - Obtener ticket por ID
- `PUT /api/tickets/{id}` - Actualizar ticket
- `DELETE /api/tickets/{id}` - Eliminar ticket
- `GET /docs` - Documentación Swagger

## Base de Datos

El backend utiliza PostgreSQL con las siguientes tablas principales:

- `tickets` - Información de tickets
- `ticket_embeddings` - Embeddings de tickets
- `attachments` - Archivos adjuntos 