#Backend/services/ticket_service.py
from backend.database.connection import get_session
from backend.schemas.ticket import TicketCreate
from backend.routes.tickets import create_ticket
from backend.embeddings.service import embed_and_store
from backend.search.service import knn_search
from backend.database.models import Ticket
from backend.utils.ticket_to_text import ticket_to_text
from twilio.rest import Client
from sqlalchemy.future import select
from sqlalchemy import func

import os
import uuid
import httpx

# --- (1) FUNCIÓN PARA CREAR TICKETS POR VOZ (opcional, la puedes comentar si no la usas) ---
async def process_voice_ticket(text: str, phone: str):
    async for session in get_session():
        payload = TicketCreate(
            TicketNumber=f"CALL-{phone[-4:]}",
            ShortDescription=text[:80],
            CreatedBy="IVR",
            Status="Nuevo"
        )
        ticket = await create_ticket(payload, session)
        # Paso 2: Embedding
        await embed_and_store(
            key=f"ticket:{ticket.id}",
            text=text,
            ticket_id=ticket.id,
            status=ticket.Status
        )
        # Paso 3: SMS (opcional)
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

# --- (2) FUNCIÓN PARA CONSULTAR TICKET Y GENERAR RESPUESTA DE VOZ ---
from backend.utils.ticket_to_text import ticket_to_text  # 👈 Agrega esta línea

async def handle_ticket_query(text: str, phone: str) -> str:
    """
    Busca el ticket más similar por embeddings y genera una respuesta en voz con ElevenLabs.
    Retorna la URL del audio para que Twilio la reproduzca.
    """
    async for session in get_session():
        print("🗣 Texto recibido desde Twilio:", text)  # 👈 PRIMER PRINT

        results = await knn_search(text, k=1, session=session)

        print("🎯 Resultado de knn_search:", results)    # 👈 SEGUNDO PRINT

        if results and results[0]["score"] < 0.55:  # <-- Puedes probar subirlo aquí
            ticket = results[0]["ticket"]
            respuesta = (
                f"Tu ticket {ticket.TicketNumber} está en estatus {ticket.Status}. "
                f"Resumen: {ticket.ShortDescription}. "
                f"Descripción completa: {ticket.Description}."
            )
        else:
            respuesta = (
                "No encontramos tickets relacionados con tu solicitud. "
                "Por favor verifica el número de ticket o proporciona más detalles."
            )
        audio_url = await synthesize_speech(respuesta)
        return audio_url


# -------------------------------------------
# Búsqueda directa por número de ticket
# -------------------------------------------
async def search_ticket_by_number(ticket_number: str) -> dict | None:
    """
    Busca un ticket por su número (comparando solo dígitos).
    """
    async for session in get_session():
        # 🔥 Limpiar el número recibido para dejar solo dígitos
        digits_only = ''.join(filter(str.isdigit, ticket_number))

        # Buscar en DB quitando todo lo que no sea dígito en TicketNumber
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

# --- (3) FUNCIÓN PARA SINTETIZAR TEXTO A VOZ (ELEVENLABS) ---
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
ELEVEN_API_URL = os.getenv("ELEVENLABS_API_URL", "https://api.elevenlabs.io")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
TMP_DIR = os.getenv("TMP_DIR", "./audio_tmp")

async def synthesize_speech(text: str) -> str:
    url = f"{ELEVEN_API_URL}/v1/text-to-speech/{ELEVEN_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"text": text, "voice_settings": {"stability": 0.75, "similarity_boost": 0.75}}
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

