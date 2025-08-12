# backend/realtime_call/inbound_routes.py

import os
import re
import logging
from urllib.parse import urlparse
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

# Preferido: solo host sin esquema (ej. "tuapp.azurewebsites.net")
PUBLIC_HOST = os.getenv("PUBLIC_HOST", "").strip()
# Compatibilidad: puede venir completo (https://, wss://, etc.)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip()


def _extract_host(value: str) -> str:
    """
    Extrae host[:port] desde una URL o un host plano.
    Acepta https://, http://, wss://, ws:// y limpia path/query/fragment.
    """
    if not value:
        return ""
    if re.match(r"^(https?|wss?)://", value, flags=re.I):
        return urlparse(value).netloc
    # Si viene plano (foo.ngrok-free.app:1234/path?x=1), corta en el primer separador
    return re.split(r"[/?#]", value, maxsplit=1)[0]


def build_ws_url(request: Request) -> str:
    """
    Construye la URL WSS pública para el WebSocket de medios.
    Prioridad:
      1) PUBLIC_HOST (host limpio, recomendado)
      2) PUBLIC_BASE_URL (se extrae el host)
      3) Cabeceras de la solicitud (X-Forwarded-Host / Host)
    """
    host = _extract_host(PUBLIC_HOST) or _extract_host(PUBLIC_BASE_URL)

    if not host:
        xf_host = request.headers.get("x-forwarded-host") or ""
        host = _extract_host(xf_host) or _extract_host(request.headers.get("host", ""))

    if not host:
        # Fallar explícito evita devolver una URL inválida a Twilio
        raise ValueError("No se pudo determinar el host público para el WebSocket.")

    ws_url = f"wss://{host}/websockets/media-stream"
    return ws_url


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
    """
    await relay_twilio(ws, tools=TOOLS)
