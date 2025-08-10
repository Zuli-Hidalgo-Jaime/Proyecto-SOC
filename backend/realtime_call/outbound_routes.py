#Backend/realtime_call/outbound_routes.py
import os
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "TU-ID.ngrok-free.app")

@router.post("/webhooks/outgoing-call-eleven")
async def handle_outgoing_call():
    response_twiml = f"""
<Response>
  <Connect>
    <Stream url="wss://{PUBLIC_BASE_URL}/websockets/media-stream" track="inbound_track" />
  </Connect>
  <Say>Hola. Iniciando conexión con el asistente de soporte.</Say>
</Response>
""".strip()
    return Response(content=response_twiml, media_type="application/xml")
