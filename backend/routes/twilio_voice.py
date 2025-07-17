# backend/routes/twilio_voice.py

from fastapi import APIRouter, Request, status, BackgroundTasks
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from backend.schemas.ticket import TicketCreate
from backend.routes.tickets import create_ticket
from backend.database.connection import get_session
from backend.embeddings.service import embed_and_store
import os
import datetime
import logging

router = APIRouter(prefix="/webhooks/twilio")
logger = logging.getLogger("twilio_voice")

# 1-A. Fase “¡Bienvenido, deje su mensaje después del beep!”
@router.post("/voice", status_code=200)
async def handle_call(request: Request):
    """
    Responde a la llamada de Twilio con un mensaje de bienvenida y solicita grabar el problema.
    """
    vr = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/webhooks/twilio/voice/transcribe",
        method="POST",
        timeout=3,
        language="es-MX",
    )
    gather.say("Hola. Por favor describa brevemente su problema luego del tono.")
    vr.append(gather)
    vr.say("No se recibió audio. Intente nuevamente.")
    return Response(content=str(vr), media_type="application/xml")

# 1-B. Fase “Twilio nos envía la transcripción”
@router.post("/voice/transcribe", status_code=200)
async def transcription(request: Request, tasks: BackgroundTasks):
    """
    Recibe la transcripción de Twilio y encola el proceso de creación de ticket.
    """
    data = await request.form()
    text = data.get("SpeechResult", "").strip()
    from_number = data.get("From")

    if not text:
        twiml = VoiceResponse()
        twiml.say("No se detectó mensaje. Por favor intente nuevamente.")
        twiml.hangup()
        return Response(content=str(twiml), media_type="application/xml")

    logger.info(f"Recibida transcripción: {text} de {from_number}")
    tasks.add_task(handle_ticket_flow, text, from_number)

    twiml = VoiceResponse()
    twiml.say("Gracias. Hemos registrado su solicitud. Adiós.")
    twiml.hangup()
    return Response(content=str(twiml), media_type="application/xml")

async def handle_ticket_flow(text: str, phone: str):
    """
    Crea ticket, genera embedding y (opcional) envía SMS de confirmación.
    """
    import datetime
    import os

    timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
    ticket_number = f"CALL-{phone[-4:]}-{timestamp}"

    session_generator = get_session()
    session = await anext(session_generator)
    try:
        payload = TicketCreate(
            TicketNumber=ticket_number,
            ShortDescription=text[:80],
            CreatedBy="IVR",
            Status="Nuevo"
        )
        ticket = await create_ticket(payload, session)
        logger.info(f"Ticket creado: {ticket.TicketNumber} para {phone}")

        # Guardar embedding
        await embed_and_store(
            key=f"ticket:{ticket.id}",
            text=text,
            ticket_id=ticket.id,
            status=ticket.Status
        )

        # Leer variables de entorno aquí
        TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
        TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
        TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

        if all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER]):
            try:
                twilio = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                twilio.messages.create(
                    to=phone,
                    from_=TWILIO_FROM_NUMBER,
                    body=f"Ticket {ticket.TicketNumber} creado. ¡Gracias por usar nuestro sistema de soporte!"
                )
                logger.info(f"SMS de confirmación enviado a {phone}")
            except Exception as e:
                logger.error(f"Error enviando SMS: {e}")
        else:
            logger.warning("Variables de entorno Twilio no definidas, no se envió SMS.")
    except Exception as e:
        logger.error(f"[handle_ticket_flow ERROR]: {e}")
    finally:
        await session.close()


