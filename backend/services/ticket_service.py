# backend/services/ticket_service.py

from backend.database.connection import get_session_context
from backend.schemas.ticket import TicketCreate
from backend.routes.tickets import create_ticket
from backend.embeddings.service import embed_and_store
from twilio.rest import Client
import os

async def process_voice_ticket(text: str, phone: str):
    # Paso 1: Crear ticket en la BD
    async with get_session_context() as session:
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
