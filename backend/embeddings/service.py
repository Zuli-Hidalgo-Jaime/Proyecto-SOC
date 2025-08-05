# backend/embeddings/service.py
"""
Funciones utilitarias para generar embeddings y almacenarlos en Redis.
"""

from backend.embeddings.openai_client import client, DEPLOY
from backend.utils.ticket_to_text import ticket_to_text
from backend.utils.redis_client import add_embedding

async def embed_and_store(key: str, ticket: dict, **meta):
    """
    Genera embedding para un ticket y lo almacena en Redis.

    Args:
        key (str): Clave en Redis para el vector.
        ticket (dict): Diccionario con los datos del ticket.
        **meta: Metadatos adicionales a guardar con el embedding.

    Returns:
        list: El vector embedding generado.
    """
    text = ticket_to_text(ticket)
    resp = await client.embeddings.create(
        model=DEPLOY,
        input=text
    )
    vector = resp.data[0].embedding
    add_embedding(key, vector, **meta)
    return vector


