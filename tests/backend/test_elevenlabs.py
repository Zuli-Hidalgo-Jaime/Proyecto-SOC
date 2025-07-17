# tests/backend/test_elevenlabs.py
# Smoke test de integración para ElevenLabs TTS

from dotenv import load_dotenv
load_dotenv()  # carga variables de .env

import os
import pytest
import httpx

# Variables de entorno
ELEVEN_API_KEY  = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
# Permite switch de región: usa EU si está configurado, si no fallará en Global
ELEVEN_API_URL  = os.getenv("ELEVENLABS_API_URL", "https://api.elevenlabs.io")

@pytest.mark.integration
def test_elevenlabs_tts_generates_audio(tmp_path):
    # Verifica que las credenciales estén definidas
    assert ELEVEN_API_KEY,  "ELEVENLABS_API_KEY no definido"
    assert ELEVEN_VOICE_ID, "ELEVENLABS_VOICE_ID no definido"

    # Construye el endpoint dinámicamente según región
    url = f"{ELEVEN_API_URL}/v1/text-to-speech/{ELEVEN_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": "Este es un test de integración con ElevenLabs",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
    }

    # Llamada a ElevenLabs
    resp = httpx.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()

    # Guarda el MP3 en un archivo temporal
    audio_file = tmp_path / "test_eleven.mp3"
    audio_file.write_bytes(resp.content)

    # Verifica que el archivo no esté vacío y tenga cabecera de MP3
    data = audio_file.read_bytes()
    assert data[:3] == b"ID3" or data[:2] == b"\xff\xfb", "El contenido no parece un MP3 válido"
