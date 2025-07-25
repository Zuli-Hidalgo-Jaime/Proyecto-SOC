# backend/embeddings/service.py

import os
from dotenv import load_dotenv
from backend.embeddings.openai_client import client, DEPLOY
from backend.utils.ticket_to_text import ticket_to_text
from backend.utils.redis_client import add_embedding

load_dotenv(override=True)

async def embed_and_store(key: str, ticket: dict, **meta):
    text = ticket_to_text(ticket)
    resp = await client.embeddings.create(
        model=DEPLOY,
        input=text
    )
    vector = resp.data[0].embedding
    add_embedding(key, vector, **meta)
    return vector

