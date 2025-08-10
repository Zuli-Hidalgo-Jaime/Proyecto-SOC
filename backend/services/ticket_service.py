#Backend/services/ticket_service.py
"""
Servicios y utilidades para procesamiento de tickets (creación por voz, consulta por embeddings, y síntesis de voz).
"""

import os
import re
import uuid
import httpx
from sqlalchemy.future import select
from sqlalchemy import func
from twilio.rest import Client

from backend.database.connection import get_session
from backend.schemas.ticket import TicketCreate
from backend.routes.tickets import create_ticket
from backend.embeddings.service import embed_and_store
from backend.search.service import knn_search
from backend.database.models import Ticket
from backend.utils.ticket_to_text import ticket_to_text
from backend.config.settings import get_settings

settings = get_settings()

# --- (1) CREAR TICKET POR VOZ ---
async def process_voice_ticket(text: str, phone: str):
    """
    Crea un ticket usando voz (texto recibido y teléfono) y envía confirmación por SMS.
    """
    async for session in get_session():
        payload = TicketCreate(
            TicketNumber=f"CALL-{phone[-4:]}",
            ShortDescription=text[:80],
            CreatedBy="IVR",
            Status="Nuevo"
        )
        ticket = await create_ticket(payload, session)
        # Embedding inicial
        ticket_dict = ticket.__dict__.copy()
        ticket_dict["attachments_ocr"] = []
        await embed_and_store(
            key=f"ticket:{ticket.id}",
            ticket=ticket_dict,
            ticket_id=ticket.id,
            status=ticket.Status
        )
        # SMS de confirmación
        TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
        TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
        TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")
        try:
            twilio = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            twilio.messages.create(
                to=phone,
                from_=TWILIO_FROM_NUMBER,
                body=f"Ticket {ticket.TicketNumber} creado. ¡Gracias por usar nuestro sistema de soporte!"
            )
        except Exception as e:
            print(f"Error enviando SMS: {e}")

# --- (2) CONSULTA DE TICKET POR EMBEDDINGS Y RESPUESTA DE VOZ ---
async def handle_ticket_query(text: str, phone: str) -> str:
    """
    1) Si detecta un número de ticket/folio en el texto, busca DIRECTO por número.
    2) Si no hay número, hace KNN (Redis) y arma respuesta.
    """
    async for session in get_session():
        LOG = __import__("logging").getLogger("ticket_service")
        LOG.info(f"[KNN] query='{text}'")

        # -------- 1) Intento directo por NÚMERO --------
        # Acepta formatos con o sin guiones/espacios: INC 250806204037-95 / INC-25080620403795 / 250806204037-95
        digits = "".join(re.findall(r"\d", text))
        if len(digits) >= 6:  # umbral bajo para aceptar números largos
            direct = await search_ticket_by_number(digits)
            if direct:
                status = direct.get("Status") or "sin estatus"
                short  = direct.get("ShortDescription") or "sin resumen"
                desc   = direct.get("Description") or "sin descripción"
                tn     = direct.get("TicketNumber") or digits
                return (f"Tu ticket {tn} está en estatus {status}. "
                        f"Resumen: {short}. Descripción: {desc}.")

        # -------- 2) Fallback: KNN por embeddings --------
        results = await knn_search(text, k=1, session=session)
        LOG.info(f"[KNN] top={results[0]['ticket'].id if results else None} "
                 f"score={results[0]['score'] if results else None} "
                 f"threshold={settings.EMBEDDING_SCORE_THRESHOLD}")

        if not results:
            return ("No encontramos tickets relacionados con tu solicitud. "
                    "Por favor verifica el número de ticket o proporciona más detalles.")

        best = results[0]
        score = float(best["score"])
        ticket = best["ticket"]

        # Acepta si pasa umbral o si es razonable (<0.60) como fallback
        if score < settings.EMBEDDING_SCORE_THRESHOLD or score < 0.60:
            desc = ticket.Description or "sin descripción"
            short = ticket.ShortDescription or "sin resumen"
            status = ticket.Status or "sin estatus"
            return (f"Tu ticket {ticket.TicketNumber} está en estatus {status}. "
                    f"Resumen: {short}. Descripción: {desc}.")

        return ("No encontramos tickets suficientemente relacionados con tu solicitud. "
                "Por favor verifica el número de ticket o proporciona más detalles.")
    
# --- (3) CONSULTA POR NÚMERO DE TICKET ---
async def search_ticket_by_number(ticket_number: str) -> dict | None:
    """
    Busca un ticket por su número, comparando solo los dígitos.
    """
    async for session in get_session():
        digits_only = ''.join(filter(str.isdigit, ticket_number))
        query = select(Ticket).where(
            func.regexp_replace(Ticket.TicketNumber, r'\D', '', 'g') == digits_only
        )
        result = await session.execute(query)
        ticket = result.scalar_one_or_none()

        if ticket:
            return {
                "TicketNumber": ticket.TicketNumber,
                "ShortDescription": ticket.ShortDescription,
                "Description": ticket.Description,
                "Status": ticket.Status,
                "Priority": ticket.Priority
            }
    return None

# --- (4) SÍNTESIS DE VOZ CON ELEVENLABS ---
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
ELEVEN_API_URL = os.getenv("ELEVENLABS_API_URL", "https://api.elevenlabs.io")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
TMP_DIR = os.getenv("TMP_DIR", "./audio_tmp")

async def synthesize_speech(text: str) -> str:
    """
    Convierte texto a voz usando ElevenLabs. Devuelve la URL pública del audio generado.
    """
    url = f"{ELEVEN_API_URL}/v1/text-to-speech/{ELEVEN_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "voice_settings": {"stability": 0.75, "similarity_boost": 0.75}
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        audio = resp.content

    os.makedirs(TMP_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}.mp3"
    path = os.path.join(TMP_DIR, filename)
    with open(path, "wb") as f:
        f.write(audio)
    print(f"Audio generado en: {path}")
    print("URL del audio para Twilio:", f"{PUBLIC_BASE_URL}/audio/{filename}")
    return f"{PUBLIC_BASE_URL}/audio/{filename}"

