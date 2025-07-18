import os, uuid
import httpx

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
ELEVEN_API_URL = os.getenv("ELEVENLABS_API_URL", "https://api.elevenlabs.io")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
TMP_DIR = os.getenv("TMP_DIR", "/tmp")

async def synthesize_speech(text: str) -> str:
    url = f"{ELEVEN_API_URL}/v1/text-to-speech/{ELEVEN_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"text": text, "voice_settings": {"stability":0.75, "similarity_boost":0.75}}
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        audio = resp.content

    filename = f"{uuid.uuid4()}.mp3"
    path = os.path.join(TMP_DIR, filename)
    with open(path, "wb") as f:
        f.write(audio)

    return f"{PUBLIC_BASE_URL}/audio/{filename}"
