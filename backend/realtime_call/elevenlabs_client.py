# backend/realtime_call/elevenlabs_client.py
"""
Cliente mínimo para obtener un WebSocket firmado de ElevenLabs ConvAI.
Lee claves desde variables de entorno y no expone secretos en código.
"""

import os
import httpx

# Variables de entorno (no hardcodear claves)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "")


async def get_signed_url() -> str:
    """
    Solicita a ElevenLabs una URL firmada de WebSocket para iniciar una conversación ConvAI.

    Returns:
        str: URL firmada (wss://...) válida para una sesión.

    Raises:
        ValueError: Si faltan variables de entorno requeridas.
        httpx.HTTPStatusError: Si la API responde con error HTTP.
    """
    if not ELEVENLABS_API_KEY or not ELEVENLABS_AGENT_ID:
        raise ValueError(
            "Faltan ELEVENLABS_API_KEY o ELEVENLABS_AGENT_ID en las variables de entorno."
        )

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.elevenlabs.io/v1/convai/conversation/get_signed_url",
            params={"agent_id": ELEVENLABS_AGENT_ID},
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["signed_url"]
