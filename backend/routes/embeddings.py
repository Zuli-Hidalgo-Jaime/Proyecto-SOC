# backend/routes/embeddings.py
"""
Rutas para crear, buscar y consultar embeddings semánticos.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from backend.embeddings.service import embed_and_store
from backend.utils.redis_client import get_vector, knn_search

router = APIRouter(prefix="/api/embeddings")

class EmbeddingIn(BaseModel):
    text: str = Field(..., example="Descripción o contenido")
    ticket_id: Optional[int] = None
    status: Optional[str] = Field(None, example="Nuevo")

@router.post("/{emb_id}", status_code=201)
async def save_embedding(emb_id: str, payload: EmbeddingIn):
    """
    Genera el embedding (Azure OpenAI) y lo guarda en Redis.
    """
    vec = await embed_and_store(
        key=emb_id,
        text=payload.text,
        ticket_id=payload.ticket_id or "",
        status=payload.status or "",
    )
    return {"vector_len": len(vec), "key": emb_id}

class SearchIn(BaseModel):
    q: str = Field(..., example="texto para buscar")
    k: int = 5
    status: Optional[str] = None

@router.post("/_search")
async def search_embeddings(body: SearchIn):
    """
    Búsqueda semántica sobre los embeddings almacenados.
    """
    filters = {"status": body.status} if body.status else {}
    hits = await knn_search(body.q, body.k, **filters)
    if not hits:
        raise HTTPException(404, "Sin resultados encontrados")
    return {"matches": hits}

@router.get("/{emb_id}")
def read_embedding(emb_id: str):
    """
    Devuelve una muestra del vector embedding para inspección/debug.
    """
    vec = get_vector(emb_id)
    if vec is None:
        raise HTTPException(404, "Embedding no encontrado")
    return {"id": emb_id, "vector": vec[:10]}
