# backend/routes/agent_tools.py
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional

# 👉 Usa la función que ya formatea "todo" o "solo campo"
from backend.services.ticket_service import handle_ticket_query

router = APIRouter(prefix="/api/agent-tools", tags=["agent-tools"])
LOG = logging.getLogger("routes.agent_tools")

class GetTicketInfoIn(BaseModel):
    query_text: str
    caller_id: Optional[str] = None  # por si quieres pasar el teléfono

@router.post("/get_ticket_info", response_class=PlainTextResponse)
async def get_ticket_info(body: GetTicketInfoIn):
    q = (body.query_text or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="query_text vacío")

    LOG.info(f"[tool] get_ticket_info q='{q}'")
    try:
        # phone es opcional; pásalo si lo usas para algo
        reply = await handle_ticket_query(q, phone=(body.caller_id or ""))
        # Texto plano para que ElevenLabs lo lea tal cual
        return PlainTextResponse(reply)
    except Exception as e:
        LOG.exception("get_ticket_info error")
        raise HTTPException(status_code=500, detail="Error procesando la consulta")
