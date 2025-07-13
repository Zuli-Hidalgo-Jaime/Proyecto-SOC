from typing import Optional
from fastapi import APIRouter, Query
from backend.search.service import knn_search

router = APIRouter()

@router.get("/search", summary="Búsqueda semántica K-NN")
async def semantic_search(
    q: str = Query(..., min_length=3, description="Texto a buscar"),
    k: int = 5,
    status: Optional[str] = None          # 👈 nuevo parámetro
):
    """
    Embebe `q`, consulta RediSearch y devuelve los `k` vecinos.
    """
    filters = {"status": status} if status else {}   # ← sólo si lo pasan
    hits = await knn_search(q, k, **filters)
    return hits
