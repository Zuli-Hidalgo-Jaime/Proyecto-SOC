#backen/routes/search
from typing import Optional

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_session   
from backend.search.service import knn_search

router = APIRouter()

@router.get("/search", summary="Búsqueda semántica K-NN")
async def semantic_search(
    q: str = Query(..., min_length=3, description="Texto a buscar"),
    k: int = 5,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),      
):
    """
    Embebe *q*, consulta RediSearch y devuelve los *k* vecinos más
    cercanos.  Si se indica `status`, filtra por esa etiqueta.
    """
    filters = {"status": status} if status else {}
    hits = await knn_search(q, k, session=session, **filters)
    return hits

