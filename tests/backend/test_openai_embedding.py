# tests/backend/test_openai_embedding.py
import os, pytest, asyncio
from backend.utils.redis_client import get_vector
from backend.embeddings.service import embed_and_store

AZ_CREDS = {"AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"}
if not AZ_CREDS.issubset(os.environ):
    pytest.skip("Azure OpenAI creds missing", allow_module_level=True)

@pytest.mark.asyncio
async def test_embed_roundtrip():
    key = "unit:test"
    vec = await embed_and_store(key, "texto de prueba", status="Nuevo")
    stored = get_vector(key)
    assert stored and len(vec) == len(stored)
