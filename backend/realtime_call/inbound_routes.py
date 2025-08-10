# backend/realtime_call/inbound_routes.py
import os
import logging
import re
import unicodedata
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from backend.realtime_call.ws_utils import relay_twilio

log = logging.getLogger("realtime_call.inbound_routes")
router = APIRouter()

# ====================== URL helper ======================
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip()

def build_ws_url(request: Request) -> str:
    """
    Devuelve wss://<host>/websockets/media-stream
    - Si hay PUBLIC_BASE_URL, la usamos (sin protocolo).
    - Si no, usamos el Host del request.
    """
    host = PUBLIC_BASE_URL or request.headers.get("host", "")
    host = host.replace("https://", "").replace("http://", "").replace("wss://", "").replace("ws://", "")
    return f"wss://{host}/websockets/media-stream"

# ====================== Normalizador/Matcher ======================
def _norm(s: str) -> str:
    t = s.lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9ñ\s#-]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def _matches_ticket_phrase(t: str) -> bool:
    patterns = [
        r"\b(quiero|quisiera|necesito|me gustaria)\s+(saber|conocer|ver|consultar|revisar)\s+(la\s+)?(informacion|info|el\s+estado|estatus|detalles?)\s+(de|del|sobre)\s+(mi|mis)\s+(tickets?|folios?|incidencias?|casos?)\b",
        r"\b(informacion|info|estado|estatus|detalles?)\s+(de|del|sobre)\s+(mi|mis)\s+(tickets?|folios?|incidencias?|casos?)\b",
        r"\b(mi|mis)\s+(ticket|folio|incidencia|caso)s?\s*(#|num|numero|nro)?\s*\d{3,}\b",
    ]
    return any(re.search(p, t) for p in patterns)

# ====================== TwiML: entrada y ruteo ======================
@router.post("/webhooks/twilio/voice/incoming", summary="Entrada de llamada (mini-gather)")
async def voice_incoming(request: Request):
    """
    1) Escucha UNA frase con STT de Twilio (sin prompt si quieres).
    2) Pasa la frase al stream como parámetro si parece consulta de ticket.
    """
    twiml = VoiceResponse()

    gather = Gather(
        input="speech",
        action="/webhooks/twilio/voice/route_speech",
        method="POST",
        language="es-MX",
        speech_timeout="auto",
    )
    # Si prefieres silencio, no agregues .say(); Twilio igual escucha.
    # gather.say("Dime: 'quiero saber la información de mi ticket'.")
    twiml.append(gather)

    # Si no habla, vuelve a intentar
    twiml.redirect("/webhooks/twilio/voice/incoming", method="POST")
    return Response(content=str(twiml), media_type="application/xml")

@router.post("/webhooks/twilio/voice/route_speech", summary="Rutea la frase al media stream")
async def voice_route_speech(request: Request):
    data = await request.form()
    transcript = (data.get("SpeechResult") or "").strip()
    norm = _norm(transcript)

    ws_url = build_ws_url(request)

    twiml = VoiceResponse()
    connect = twiml.connect()
    stream = connect.stream(url=ws_url)

    # Si la frase es de consulta de ticket, pasamos el texto inicial
    if _matches_ticket_phrase(norm):
        stream.parameter(name="init_knn_text", value=transcript)

    return Response(content=str(twiml), media_type="application/xml")

# ====================== WebSocket del media stream ======================
@router.websocket("/websockets/media-stream")
async def media_stream(ws: WebSocket):
    await relay_twilio(ws)

# ====================== Compat: endpoint viejo ======================
@router.post("/webhooks/incoming-call-eleven")
async def incoming_compat():
    # Redirige al nuevo flujo con mini-gather
    twiml = VoiceResponse()
    twiml.redirect("/webhooks/twilio/voice/incoming", method="POST")
    return Response(content=str(twiml), media_type="application/xml")

