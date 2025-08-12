import os
import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse

from backend.realtime_call.ws_utils import relay_twilio
from backend.services.ticket_service import (
    handle_ticket_query,
    process_voice_ticket,
)

log = logging.getLogger("realtime_call.inbound_routes")
router = APIRouter()

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip()


def build_ws_url(request: Request) -> str:
    """
    Construye la URL WSS pública para el WebSocket de medios, derivada de
    PUBLIC_BASE_URL (si existe) o del encabezado Host de la solicitud.

    Args:
        request: Objeto Request de FastAPI.

    Returns:
        URL WSS absoluta para /websockets/media-stream.
    """
    host = PUBLIC_BASE_URL or request.headers.get("host", "")
    host = (
        host.replace("https://", "")
        .replace("http://", "")
        .replace("wss://", "")
        .replace("ws://", "")
    )
    return f"wss://{host}/websockets/media-stream"


TOOLS: List[Dict[str, Any]] = [
    {
        "name": "handle_ticket_query",
        "func": handle_ticket_query,
        "schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Consulta del usuario en lenguaje natural."},
                "phone": {"type": "string", "description": "Número del llamante (E.164)."},
            },
            "required": ["text", "phone"],
        },
        "description": "Busca ticket por número directo o por similitud (KNN) y devuelve respuesta formateada.",
    },
    {
        "name": "process_voice_ticket",
        "func": process_voice_ticket,
        "schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Descripción breve dictada por el usuario."},
                "phone": {"type": "string", "description": "Número del llamante (E.164)."},
            },
            "required": ["text", "phone"],
        },
        "description": "Crea un ticket a partir de voz y envía confirmación por SMS.",
    },
]


@router.post("/webhooks/twilio/voice/incoming", summary="Entrada de llamada → streaming inmediato")
async def voice_incoming(request: Request) -> Response:
    """
    Endpoint principal para Twilio Voice. Genera TwiML con <Connect><Stream>
    (solo track de entrada) hacia el WebSocket de medios.

    Args:
        request: Solicitud HTTP entrante desde Twilio.

    Returns:
        Respuesta XML (TwiML) para iniciar el stream WebSocket.
    """
    ws_url = build_ws_url(request)
    log.info("WS URL generado: %s", ws_url)
    vr = VoiceResponse()
    connect = vr.connect()
    connect.stream(url=ws_url, track="inbound_track")
    return Response(str(vr), media_type="application/xml")


@router.post("/webhooks/incoming-call-eleven")
async def incoming_compat(request: Request) -> Response:
    """
    Endpoint compatible para integraciones previas. Genera el mismo TwiML que
    /webhooks/twilio/voice/incoming (solo track de entrada).

    Args:
        request: Solicitud HTTP entrante.

    Returns:
        Respuesta XML (TwiML) para iniciar el stream WebSocket.
    """
    ws_url = build_ws_url(request)
    log.info("[compat] WS URL generado: %s", ws_url)
    vr = VoiceResponse()
    connect = vr.connect()
    connect.stream(url=ws_url, track="inbound_track")
    return Response(str(vr), media_type="application/xml")


@router.websocket("/websockets/media-stream")
async def media_stream(ws: WebSocket) -> None:
    """
    WebSocket de medios que enlaza el stream de Twilio con ElevenLabs,
    inyectando las herramientas declaradas en TOOLS.

    Args:
        ws: Conexión WebSocket de FastAPI.
    """
    await relay_twilio(ws, tools=TOOLS)

