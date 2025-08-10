#elevenlabs_client
import os
import httpx

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "")  # puede llamarse AGENT_ID o VOICE_ID, pon el correcto

async def get_signed_url() -> str:
    if not ELEVENLABS_API_KEY or not ELEVENLABS_AGENT_ID:
        raise ValueError("Faltan ELEVENLABS_API_KEY o ELEVENLABS_VOICE_ID en tus variables de entorno.")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.elevenlabs.io/v1/convai/conversation/get_signed_url",
            params={"agent_id": ELEVENLABS_AGENT_ID},
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["signed_url"]
