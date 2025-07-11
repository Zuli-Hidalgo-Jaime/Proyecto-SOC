from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.utils.redis_client import add_embedding, knn_search, get_vector

router = APIRouter(prefix="/api/embeddings")

# Modelo para guardar embeddings
class EmbeddingIn(BaseModel):
    vector: List[float]
    ticket_id: Optional[int] = None
    status: Optional[str] = None

@router.post("/{emb_id}", status_code=201)
def save_embedding(emb_id: str, payload: EmbeddingIn):
    """
    Guarda un embedding en Redis con ID y metadatos opcionales
    """
    add_embedding(
        emb_id,
        payload.vector,
        ticket_id=payload.ticket_id or "",
        status=payload.status or ""
    )
    return {"msg": "Embedding guardado correctamente", "id": emb_id}

# Modelo para búsqueda KNN
class SearchIn(BaseModel):
    vector: List[float]
    k: int = 5
    status: Optional[str] = None

@router.post("/_search")
def search_embeddings(body: SearchIn):
    """
    Realiza búsqueda KNN sobre los embeddings almacenados
    """
    filters = {}
    if body.status:
        filters["status"] = body.status

    hits = knn_search(body.vector, body.k, **filters)
    if not hits:
        raise HTTPException(404, "Sin resultados encontrados")
    return {"matches": hits}

@router.get("/{emb_id}")
def read_embedding(emb_id: str):
    """
    Devuelve un embedding almacenado por su ID
    """
    vec = get_vector(emb_id)
    if vec is None:
        raise HTTPException(404, "Embedding no encontrado")
    return {"id": emb_id, "vector": vec}
