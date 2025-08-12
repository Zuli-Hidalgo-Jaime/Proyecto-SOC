import os
import logging
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse

# ⬇️ IMPORTA tu puente
from backend.realtime_call.ws_utils import relay_twilio

# ⬇️ IMPORTA TUS SERVICIOS (los que pegaste)
from backend.services.ticket_service import (
    handle_ticket_query,
    process_voice_ticket,
)

log = logging.getLogger("realtime_call.inbound_routes")
router = APIRouter()

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip()

def build_ws_url(request: Request) -> str:
    host = PUBLIC_BASE_URL or request.headers.get("host", "")
    host = host.replace("https://", "").replace("http://", "").replace("wss://", "").replace("ws://", "")
    return f"wss://{host}/websockets/media-stream"

# 🔧 ===== TOOLS DEFINITIONS PARA ELEVENLABS =====
TOOLS = [
    {
        "name": "handle_ticket_query",
        "func": handle_ticket_query,
        "schema": {
            "type": "object",
            "properties": {
                "text":  {"type": "string", "description": "Consulta del usuario en lenguaje natural."},
                "phone": {"type": "string", "description": "Número del llamante (E.164)."}
            },
            "required": ["text", "phone"]
        },
        "description": "Busca ticket por número directo o por similitud (KNN) y devuelve respuesta formateada."
    },
    {
        "name": "process_voice_ticket",
        "func": process_voice_ticket,
        "schema": {
            "type": "object",
            "properties": {
                "text":  {"type": "string", "description": "Descripción breve dictada por el usuario."},
                "phone": {"type": "string", "description": "Número del llamante (E.164)."}
            },
            "required": ["text", "phone"]
        },
        "description": "Crea un ticket a partir de voz y envía confirmación por SMS."
    }
]
# ===============================================

@router.post("/webhooks/twilio/voice/incoming", summary="Entrada de llamada → streaming inmediato")
async def voice_incoming(request: Request):
    ws_url = build_ws_url(request)
    log.info(f"WS URL generado: {ws_url}")
    vr = VoiceResponse()
    connect = vr.connect()
    # ✅ SOLO ENTRADA (como cuando sonaba bien)
    connect.stream(url=ws_url, track="inbound_track")
    return Response(str(vr), media_type="application/xml")

@router.post("/webhooks/incoming-call-eleven")
async def incoming_compat(request: Request):
    ws_url = build_ws_url(request)
    log.info(f"[compat] WS URL generado: {ws_url}")
    vr = VoiceResponse()
    connect = vr.connect()
    # ✅ SOLO ENTRADA (igual que arriba)
    connect.stream(url=ws_url, track="inbound_track")
    return Response(str(vr), media_type="application/xml")

@router.websocket("/websockets/media-stream")
async def media_stream(ws: WebSocket):
    # ⬇️ PASA LOS TOOLS AL PUENTE
    await relay_twilio(ws, tools=TOOLS)

