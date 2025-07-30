# backend/search/service.py -
import os
from typing import Any, Dict, List, Optional

import numpy as np
from redis.commands.search.query import Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.embeddings.service import client
from backend.utils.redis_client import redis_client
from backend.database.models import Ticket            # modelo SQLAlchemy

INDEX  = "embeddings_idx"
DEPLOY = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]

def to_binary(vec: List[float]) -> bytes:
    return np.array(vec, dtype=np.float32).tobytes()


async def knn_search(
    text: str,
    k: int = 5,
    session: Optional[AsyncSession] = None,  # None ⇒ sólo key/score
    **filters,
) -> List[Dict[str, Any]]:
    # 1️⃣ Generar embedding del texto
    resp = await client.embeddings.create(model=DEPLOY, input=text)
    qvec = resp.data[0].embedding

    # 2️⃣ Build filtro RediSearch
    filter_str = (
        " ".join(f"@{k}:{{{v}}}" for k, v in filters.items()) or "*"
    )
    query_str = f"{filter_str}=>[KNN {k} @vector $V AS score]"

    params = {"V": to_binary(qvec)}
    q = (
        Query(query_str)
        .return_fields("__key", "score")
        .sort_by("score")
        .dialect(2)
    )
    res = redis_client.ft(INDEX).search(q, query_params=params)

    # 3️⃣ Si NO se pasó sesión ⇒ devolver sólo key/score (tests, uso simple)
    if session is None:
        return [
            {
                "key":  doc["__key"].removeprefix("emb:"),
                "score": float(doc["score"]),
            }
            for doc in res.docs
        ]

    # 4️⃣ Con sesión ⇒ mapear IDs y consultar la BD
    id2score = {}
    for doc in res.docs:
        key = doc["__key"].removeprefix("emb:")
        if key.startswith("ticket:"):
            try:
                tid = int(key.split(":")[1])
                id2score[tid] = float(doc["score"])
            except ValueError:
                # Claves que no siguen formato ticket:<id> se ignoran
                continue

    if not id2score:
        return []

    stmt = select(Ticket).where(Ticket.id.in_(id2score.keys()))
    result = await session.execute(stmt)
    tickets = result.scalars().all()

    # 5️⃣ Ordenar según score original
    return sorted(
        (
            {"ticket": t, "score": id2score[t.id]}
            for t in tickets
        ),
        key=lambda x: x["score"]
    )

