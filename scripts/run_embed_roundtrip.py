# run_embed_roundtrip.py  (guárdalo donde quieras o copia en el REPL)

import asyncio, os, json
from backend.embeddings.service import embed_and_store
from backend.utils.redis_client import get_vector

async def demo():
    key   = "manual:test"
    text  = "¡Hola, esto es solo una prueba rápida!"

    vec   = await embed_and_store(key, text, status="Nuevo")
    print(f"Embedding length   : {len(vec)}")          # debería ser 1536
    print(f"Primeros 5 valores : {vec[:5]}")

    vec_redis = get_vector(key)
    print("¿Redis lo devolvió?:", vec_redis is not None)
    print("Coinciden longitudes?", len(vec) == len(vec_redis))

asyncio.run(demo())
