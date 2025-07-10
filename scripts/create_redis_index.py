# scripts/create_redis_index.py
import redis
from redisvl.index import SearchIndex

# 1) Conexión
r = redis.Redis(host="localhost", port=6379, decode_responses=False)

# 2) Esquema del índice
index = SearchIndex(
    name="embeddings_idx",
    prefix="emb:",                 # todas las keys comienzan con emb:
    storage_type="hash",
    fields=[
        {
            "name": "vector",
            "type": "vector",
            "attrs": {
                "algorithm": "HNSW",            # o "FLAT"
                "dims": 1536,                   # <-- ajusta a tus embeddings
                "distance_metric": "COSINE",
                "datatype": "FLOAT32",          # 4 bytes * dims
                "initial_cap": 10_000,
            },
        },
        # (opcional) metadatos para filtrar
        {"name": "ticket_id", "type": "tag"},
        {"name": "status", "type": "tag"},
    ],
)

# 3) Crear (idempotente)
if not index.exists(r):
    index.create(r)
    print("Índice creado")
else:
    print("Índice existente")
