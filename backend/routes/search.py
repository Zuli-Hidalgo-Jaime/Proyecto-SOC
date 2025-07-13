# backend/routes/search.py
from fastapi import APIRouter, Query
from backend.search.service import knn_search

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/", summary="Búsqueda semántica K-NN")
async def search(q: str = Query(..., min_length=3), k: int = 5):
    return await knn_search(q, k=k)
