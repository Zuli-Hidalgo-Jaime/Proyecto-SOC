# backend/routes/agent_tools.py
"""
Endpoints de herramientas para el agente (integración con ElevenLabs/ConvAI).

Provee un endpoint HTTP que ejecuta la función local `handle_ticket_query`
y retorna texto plano para que el agente lo lea tal cual.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from backend.services.ticket_service import handle_ticket_query

router = APIRouter(prefix="/api/agent-tools", tags=["agent-tools"])
LOG = logging.getLogger("routes.agent_tools")


class GetTicketInfoIn(BaseModel):
    """
    Modelo de entrada para obtener información de tickets.

    Atributos:
        query_text: Texto de consulta (número de ticket o descripción).
        caller_id:  (Opcional) Número del llamante en formato E.164.
    """
    query_text: str
    caller_id: Optional[str] = None


@router.post("/get_ticket_info", response_class=PlainTextResponse)
async def get_ticket_info(body: GetTicketInfoIn) -> PlainTextResponse:
    """
    Ejecuta la búsqueda de ticket usando `handle_ticket_query` y devuelve
    la respuesta en texto plano.

    Args:
        body: Payload con `query_text` y opcionalmente `caller_id`.

    Returns:
        PlainTextResponse con el texto a locutar por el agente.

    Raises:
        HTTPException(400): Si `query_text` está vacío.
        HTTPException(500): Si ocurre un error interno al procesar.
    """
    q = (body.query_text or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="query_text vacío")

    LOG.info("[tool] get_ticket_info q='%s'", q)
    try:
        reply = await handle_ticket_query(q, phone=(body.caller_id or ""))
        return PlainTextResponse(reply)
    except Exception:
        LOG.exception("get_ticket_info error")
        raise HTTPException(status_code=500, detail="Error procesando la consulta")
