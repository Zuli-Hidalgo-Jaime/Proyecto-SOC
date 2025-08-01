#backend/utils/redis_client.py
"""
Redis helpers: set/get embeddings y KNN search
"""
import redis
import numpy as np
from typing import List
from redisvl.query import VectorQuery
from redis.commands.search.field import VectorField, TagField
from redis.exceptions import ResponseError
from redis.commands.search.indexDefinition import IndexDefinition
from backend.config.settings import get_settings
settings = get_settings()

REDIS_HOST = settings.REDIS_HOST
REDIS_PORT = settings.REDIS_PORT
INDEX_NAME = settings.REDIS_INDEX_NAME
VECTOR_DIM = 1536


r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
redis_client = r

# ───────── Crear índice si no existe ─────────
def _ensure_index():
    try:
        r.ft(INDEX_NAME).info()        
    except ResponseError:
        print("- Creando índice Redis-Vector …")
        r.ft(INDEX_NAME).create_index(
            fields=[
                VectorField(
                    "vector",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": VECTOR_DIM,
                        "DISTANCE_METRIC": "COSINE"
                    }
                ),
                TagField("status"),
                TagField("ticket_id"),
            ],
            definition=IndexDefinition(prefix=["emb:"])
        )

_ensure_index()   # ← se ejecuta al importar el módulo

# Almacenar

def _to_float32_bytes(v: List[float]) -> bytes:
    return np.array(v, dtype=np.float32).tobytes()

def add_embedding(key: str, vector: list[float], **meta):
    redis_key = f"emb:{key}"          # ← debe ser emb:, no embeddings:
    redis_client.hset(
        redis_key,
        mapping={
            "vector": _to_float32_bytes(vector),
            **meta,
        },
    )

# Búsqueda #

def knn_search(query: List[float], k: int = 5, **filters):
    """
    Devuelve [(key, score), …] ordenados por similitud (cosine).
    filters => {'status': 'Nuevo'} convierte a @status:{Nuevo}
    """
    f32_query = _to_float32_bytes(query)

    # Construir filtro tag si se pasan kwargs
    filter_str = " ".join([f"@{k}:{{{v}}}" for k, v in filters.items()])
    query_str  = f"{filter_str}=>[KNN {k} @vector $BLOB AS score]"

    q = VectorQuery(query_str, return_fields=["__key", "score"]) \
          .sort_by("score") \
          .dialect(2)

    res = q.execute(r, INDEX_NAME, {"BLOB": f32_query})
    return [(doc["__key"].decode().removeprefix("emb:"), float(doc["score"]))
            for doc in res.docs]

def get_vector(key: str):
    raw = r.hget(f"emb:{key}", "vector")
    if raw is None:
        return None
    return np.frombuffer(raw, dtype=np.float32).tolist()

__all__ = ["add_embedding", "knn_search", "get_vector", "redis_client"]
