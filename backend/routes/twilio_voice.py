import re
from fastapi import APIRouter, Request, status
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather

from backend.services.ticket_service import (
    handle_ticket_query,
    search_ticket_by_number,
    synthesize_speech,
    PUBLIC_BASE_URL,
)

import logging

router = APIRouter(prefix="/webhooks/twilio")
logger = logging.getLogger("twilio_voice")

WELCOME_AUDIO_URL = None
MENU_AFTER_TICKET_AUDIO_URL = None
INVALID_OPTION_AUDIO_URL = None
GOODBYE_AUDIO_URL = None


# ---------------------------
# Endpoint inicial de la llamada
# ---------------------------
@router.post("/voice", status_code=200)
async def handle_call(request: Request):
    """
    Responde a la llamada con mensaje de bienvenida.
    Solo ofrece opciones 1 y 2 al inicio.
    """
    global WELCOME_AUDIO_URL

    if not WELCOME_AUDIO_URL:
        welcome_text = (
            "Hola. Bienvenido al sistema de soporte. "
            "Presione uno para ingresar el número de ticket con el teclado, "
            "o presione dos para describir su problema con su voz."
        )
        WELCOME_AUDIO_URL = await synthesize_speech(welcome_text)

    vr = VoiceResponse()
    vr.play(WELCOME_AUDIO_URL)

    gather = Gather(
        num_digits=1,
        action="/webhooks/twilio/voice/menu",
        method="POST",
        timeout=6,
    )
    vr.append(gather)

    fallback_audio_url = await synthesize_speech(
        "No se detectó ninguna entrada. Gracias por llamar."
    )
    vr.play(fallback_audio_url)
    vr.hangup()
    return Response(content=str(vr), media_type="application/xml")


# ---------------------------
# Endpoint para manejar opción del menú inicial
# ---------------------------
@router.post("/voice/menu", status_code=200)
async def handle_menu_choice(request: Request):
    """
    Procesa la opción seleccionada:
    1 = ingresar número de ticket
    2 = describir problema
    3 = finalizar llamada
    """
    global INVALID_OPTION_AUDIO_URL, GOODBYE_AUDIO_URL

    data = await request.form()
    choice = data.get("Digits", "").strip()

    twiml = VoiceResponse()

    if choice == "1":
        # Fluir hacia el ingreso de número de ticket
        gather = Gather(
            input="dtmf",
            action="/webhooks/twilio/voice/process_input",
            method="POST",
            timeout=8,
            num_digits=20,
            language="es-MX",
        )
        vr_text = "Por favor, ingrese su número de ticket usando el teclado."
        audio_url = await synthesize_speech(vr_text)
        twiml.play(audio_url)
        twiml.append(gather)

    elif choice == "2":
        # Fluir hacia el dictado de problema (embeddings)
        vr_text = "Describa a continuación brevemente su problema."
        audio_url = await synthesize_speech(vr_text)
        twiml.play(audio_url)
        gather = Gather(
            input="speech",
            action="/webhooks/twilio/voice/process_speech",
            method="POST",
            timeout=6,
            language="es-MX",
        )
        twiml.append(gather)

    elif choice == "3":
        if not GOODBYE_AUDIO_URL:
            goodbye_text = "Gracias por utilizar nuestro sistema de soporte. Hasta pronto."
            GOODBYE_AUDIO_URL = await synthesize_speech(goodbye_text)
        twiml.play(GOODBYE_AUDIO_URL)
        twiml.hangup()

    else:
        if not INVALID_OPTION_AUDIO_URL:
            invalid_text = (
                "Opción no válida. Presione uno para ingresar número de ticket, "
                "dos para describir su problema, o tres para finalizar la llamada."
            )
            INVALID_OPTION_AUDIO_URL = await synthesize_speech(invalid_text)
        twiml.play(INVALID_OPTION_AUDIO_URL)
        twiml.redirect("/webhooks/twilio/voice/menu")

    return Response(content=str(twiml), media_type="application/xml")

# ---------------------------
# Endpoint para procesar DTMF (teclado)
# ---------------------------
@router.post("/voice/process_input", status_code=200)
async def process_input(request: Request):
    """
    Procesa la entrada del usuario con número de ticket.
    """
    data = await request.form()
    digits = data.get("Digits", "").strip()

    twiml = VoiceResponse()

    if digits:
        clean_digits = re.sub(r"\D", "", digits)
        ticket_number = f"INC-{clean_digits}"

        ticket_info = await search_ticket_by_number(ticket_number)
        if ticket_info:
            respuesta = (
                f"El ticket {ticket_info['TicketNumber']} tiene el estado {ticket_info['Status']}, "
                f"prioridad {ticket_info['Priority']}. "
                f"Descripción corta: {ticket_info['ShortDescription']}. "
                f"Descripción completa: {ticket_info['Description'] or 'No hay una descripción registrada para este ticket'}."

            )
            audio_url = await synthesize_speech(respuesta)
            twiml.play(audio_url)
        else:
            not_found_audio = await synthesize_speech(
                "No encontramos un ticket con ese número. Por favor verifique e intente nuevamente."
            )
            twiml.play(not_found_audio)

        # Después de dar info, mostrar menú extendido (1, 2, 3)
        await add_post_ticket_menu(twiml)

    return Response(content=str(twiml), media_type="application/xml")


# ---------------------------
# Endpoint para procesar voz
# ---------------------------
@router.post("/voice/process_speech", status_code=200)
async def process_speech(request: Request):
    """
    Procesa el dictado de problema (embeddings).
    """
    data = await request.form()
    speech_text = data.get("SpeechResult", "").strip()
    from_number = data.get("From")

    twiml = VoiceResponse()

    if not speech_text:
        fallback_audio_url = await synthesize_speech(
            "No se detectó ningún mensaje. Intente nuevamente."
        )
        twiml.play(fallback_audio_url)
        twiml.redirect("/webhooks/twilio/voice/menu")
        return Response(content=str(twiml), media_type="application/xml")

    audio_url = await handle_ticket_query(speech_text, from_number)
    twiml.play(audio_url)

    # Después de dar info, mostrar menú extendido (1, 2, 3)
    await add_post_ticket_menu(twiml)
    return Response(content=str(twiml), media_type="application/xml")


# ---------------------------
# Menú extendido después de un ticket
# ---------------------------
async def add_post_ticket_menu(twiml: VoiceResponse):
    """
    Añade un menú extendido (1, 2, 3) para continuar o salir.
    """
    global MENU_AFTER_TICKET_AUDIO_URL, GOODBYE_AUDIO_URL

    if not MENU_AFTER_TICKET_AUDIO_URL:
        menu_text = (
            "Presione uno para ingresar otro número de ticket, "
            "presione dos para describir otro problema, "
            "o presione tres para finalizar la llamada."
        )
        MENU_AFTER_TICKET_AUDIO_URL = await synthesize_speech(menu_text)

    twiml.play(MENU_AFTER_TICKET_AUDIO_URL)

    gather = Gather(
        num_digits=1,
        action="/webhooks/twilio/voice/menu",
        method="POST",
        timeout=6,
    )
    twiml.append(gather)








