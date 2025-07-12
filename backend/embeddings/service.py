# backend/embeddings/service.py
import os
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from backend.utils.redis_client import add_embedding

load_dotenv(override=True) 

DEPLOY     = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]
ENDPOINT   = os.environ["AZURE_OPENAI_ENDPOINT"]
API_KEY    = os.environ["AZURE_OPENAI_API_KEY"]
API_VER    = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

client = AsyncAzureOpenAI(
    api_key        = API_KEY,
    azure_endpoint = ENDPOINT,          # <<-- NO base_url
    api_version    = API_VER,           # >= 2024-02-15-preview
)

async def embed_and_store(key: str, text: str, **meta):
    resp = await client.embeddings.create(
        model=DEPLOY,                   # nombre del deployment
        input=text
    )
    vector = resp.data[0].embedding
    add_embedding(key, vector, **meta)
    return vector

