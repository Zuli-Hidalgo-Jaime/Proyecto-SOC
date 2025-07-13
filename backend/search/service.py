# backend/search/service.py
import os, numpy as np
from redis.commands.search.query import Query
from backend.embeddings.service import client
from backend.utils.redis_client import redis_client

INDEX  = "embeddings_idx"                                # nombre de tu índice
DEPLOY = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]

def to_binary(vec: list[float]) -> bytes:
    return np.array(vec, dtype=np.float32).tobytes()

async def knn_search(text: str, k: int = 5, status: str = "Nuevo"):
    # 1. Embedding del texto (no se guarda)
    resp = await client.embeddings.create(model=DEPLOY, input=text)
    qvec = resp.data[0].embedding

    # 2. Construir la consulta RediSearch
    filter_str = f"@status:{{{status}}}" if status else ""
    query_str  = f"{filter_str}=>[KNN {k} @vector $V AS score]"

    params = {"V": to_binary(qvec)}           # parámetros binarios
    q = (
        Query(query_str)
        .return_fields("__key", "score")
        .sort_by("score")
        .dialect(2)                           # activa sintaxis RediSearch 2
    )

    res = redis_client.ft(INDEX).search(q, query_params=params)

# Normalizar resultados
    return [
        {
            "key": (doc["__key"].removeprefix("emb:")),  # __key ya es str
            "score": float(doc["score"]),
        }
        for doc in res.docs
    ]
