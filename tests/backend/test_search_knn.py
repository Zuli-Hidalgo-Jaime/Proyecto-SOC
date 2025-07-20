# tests/backend/test_search_knn.py
import pytest, asyncio
from backend.embeddings.service import embed_and_store
from backend.search.service import knn_search

@pytest.mark.asyncio
async def test_knn_roundtrip():
    key = "unit:knn"
    text = "prueba de índice"
    await embed_and_store(key, text, status="Nuevo")

    results = await knn_search(text, k=1)
    assert results and results[0]["key"] == key
