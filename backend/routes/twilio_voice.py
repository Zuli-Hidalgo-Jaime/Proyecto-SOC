from fastapi import APIRouter, Request, status
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather

from backend.services.ticket_service import handle_ticket_query, synthesize_speech  # <-- Importa ambas funciones

import logging

router = APIRouter(prefix="/webhooks/twilio")
logger = logging.getLogger("twilio_voice")

WELCOME_AUDIO_URL = None

@router.post("/voice", status_code=200)
async def handle_call(request: Request):
    """
    Responde a la llamada de Twilio con mensaje de bienvenida (voz ElevenLabs)
    y solicita grabar el problema con más tiempo para hablar.
    """
    global WELCOME_AUDIO_URL

    # Si aún no has generado el audio, hazlo y guárdalo
    if not WELCOME_AUDIO_URL:
        welcome_text = "Hola. Por favor describa brevemente su problema luego del tono."
        WELCOME_AUDIO_URL = await synthesize_speech(welcome_text)

    vr = VoiceResponse()
    vr.play(WELCOME_AUDIO_URL)
    # DA MÁS TIEMPO PARA HABLAR (timeout=8)
    gather = Gather(
        input="speech",
        action="/webhooks/twilio/voice/transcribe",
        method="POST",
        timeout=4,
        language="es-MX",
    )
    # Ya no se usa .say aquí, porque ya se reproduce el audio real de ElevenLabs
    vr.append(gather)
    vr.say("No se recibió audio. Intente nuevamente.")  # fallback por si no habla
    return Response(content=str(vr), media_type="application/xml")

@router.post("/voice/transcribe", status_code=200)
async def transcription(request: Request):
    """
    Recibe la transcripción de Twilio, busca el ticket más similar y responde con voz.
    Ya no crea tickets nuevos.
    """
    data = await request.form()
    text = data.get("SpeechResult", "").strip()
    from_number = data.get("From")

    if not text:
        twiml = VoiceResponse()
        twiml.say("No se detectó mensaje. Por favor intente nuevamente.")
        twiml.hangup()
        return Response(content=str(twiml), media_type="application/xml")

    # Busca el ticket más parecido y genera el audio de respuesta
    audio_url = await handle_ticket_query(text, from_number)

    twiml = VoiceResponse()
    twiml.play(audio_url)
    twiml.hangup()
    return Response(content=str(twiml), media_type="application/xml")

# -------------------------------------------------------------------------
# Ya no se generan tickets a través de llamada - OBSOLETO
# -------------------------------------------------------------------------
# async def handle_ticket_flow(...): ...   # Eliminado/obsoleto

