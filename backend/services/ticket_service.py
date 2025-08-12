# backend/services/ticket_service.py
"""
Servicios y utilidades para procesamiento de tickets:
- Creación por voz
- Consulta semántica (KNN) o directa por número
- Respuesta formateada según los campos solicitados por el usuario
- (Opcional) síntesis de voz (no usada en RT)
"""

import os
import re
import uuid
import httpx
import unicodedata
import logging
from types import SimpleNamespace
from typing import List, Optional

from sqlalchemy.future import select
from sqlalchemy import func
from twilio.rest import Client

from backend.database.connection import get_session
from backend.schemas.ticket import TicketCreate
from backend.routes.tickets import create_ticket
from backend.embeddings.service import embed_and_store
from backend.search.service import knn_search
from backend.database.models import Ticket
from backend.utils.ticket_to_text import ticket_to_text  # (usado para embeddings)
from backend.config.settings import get_settings

settings = get_settings()
LOG = logging.getLogger("ticket_service")

# ==========================
# Selección y formato de campos
# ==========================

FIELD_LABELS = {
    "TicketNumber": "Ticket",
    "Status": "Estatus",
    "ShortDescription": "Resumen",
    "Description": "Descripción",
    "Priority": "Prioridad",
    "Impact": "Impacto",
    "Urgency": "Urgencia",
    "Severity": "Severidad",
    "Category": "Categoría",
    "Subcategory": "Subcategoría",
    "AssignmentGroup": "Grupo asignado",
    "AssignedTo": "Responsable",
    "Company": "Empresa",
    "Channel": "Canal",
    "Folio": "Folio",
}

# tokens de lenguaje natural → nombre de campo en DB
FIELD_MAP = {
    # número
    "numero": "TicketNumber",
    "número": "TicketNumber",
    "ticket": "TicketNumber",
    "folio": "Folio",
    # estado
    "estado": "Status",
    "estatus": "Status",
    "status": "Status",
    # resumen / título
    "resumen": "ShortDescription",
    "titulo": "ShortDescription",
    "título": "ShortDescription",
    "descripcion corta": "ShortDescription",
    "descripción corta": "ShortDescription",
    # descripción
    "descripcion": "Description",
    "descripción": "Description",
    "detalle": "Description",
    "detalles": "Description",
    # otros
    "prioridad": "Priority",
    "impacto": "Impact",
    "urgencia": "Urgency",
    "severidad": "Severity",
    "categoria": "Category",
    "categoría": "Category",
    "subcategoria": "Subcategory",
    "subcategoría": "Subcategory",
    "grupo": "AssignmentGroup",
    "asignado": "AssignmentGroup",
    "responsable": "AssignedTo",
    "empresa": "Company",
    "canal": "Channel",
}

DEFAULT_FIELDS = ["Status", "ShortDescription", "Description"]
ALL_FIELDS_ORDER = [
    "TicketNumber",
    "Status",
    "ShortDescription",
    "Description",
    "Priority",
    "Impact",
    "Urgency",
    "Severity",
    "Category",
    "Subcategory",
    "AssignmentGroup",
    "AssignedTo",
    "Company",
    "Channel",
    "Folio",
]


def _norm(s: str) -> str:
    """
    Normaliza texto: minúsculas, elimina acentos, limpia caracteres y colapsa espacios.
    """
    t = s.lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9ñ\s#-]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def parse_requested_fields(text: str) -> Optional[List[str]]:
    """
    Detecta los campos solicitados en lenguaje natural.

    Returns:
        - ['__ALL__'] si pide TODO
        - None si no detecta campos explícitos (usaremos DEFAULT_FIELDS)
        - Lista de campos específicos si los menciona
    """
    t = _norm(text)

    # todo / información completa
    if re.search(
        r"\b("
        r"todo|toda\s+la\s+info(?:rmaci[oó]n)?|"
        r"info(?:rmaci[oó]n)?\s+complet[ao]s?|"
        r"detalles?\s+complet[ao]s?|"
        r"todos?\s+los?\s+detalles?|"
        r"todos?\s+los?\s+campos?|"
        r"informaci[oó]n\s+total|"
        r"todo\s+el\s+detalle|"
        r"todo\s+por\s+favor"
        r")\b",
        t,
    ):
        return ["__ALL__"]

    found: List[str] = []
    only = bool(
        re.search(
            r"\b(solo|solamente|unicamente|únicamente|nada mas|nada más|solo el|solo la)\b", t
        )
    )

    # multi-palabra primero (ej. "descripcion corta")
    for token, field in FIELD_MAP.items():
        if " " in token and re.search(rf"\b{re.escape(token)}\b", t):
            if field not in found:
                found.append(field)

    # luego tokens simples
    for token, field in FIELD_MAP.items():
        if " " in token:
            continue
        if re.search(rf"\b{re.escape(token)}\b", t):
            if field not in found:
                found.append(field)

    if found:
        return found if only else found

    return None


def format_ticket_reply(ticket_obj, fields: Optional[List[str]]) -> str:
    """
    Construye la respuesta con los campos solicitados:
      - None        -> DEFAULT_FIELDS
      - ['__ALL__'] -> todos los campos
      - ['Status', 'Priority'] -> solo esos
    Siempre antepone "Ticket <num>:" si está disponible.
    """
    if fields == ["__ALL__"]:
        fields_to_use = [f for f in ALL_FIELDS_ORDER if f in FIELD_LABELS]
    elif fields:
        fields_to_use = fields
    else:
        fields_to_use = DEFAULT_FIELDS

    parts: List[str] = []
    tn = getattr(ticket_obj, "TicketNumber", None)
    if tn:
        parts.append(f"Ticket {tn}:")

    for f in fields_to_use:
        if not hasattr(ticket_obj, f):
            continue
        val = getattr(ticket_obj, f) or "sin dato"
        label = FIELD_LABELS.get(f, f)
        parts.append(f"{label}: {val}.")

    return " ".join(parts)


# ==========================
# (1) CREAR TICKET POR VOZ
# ==========================

async def process_voice_ticket(text: str, phone: str):
    """
    Crea un ticket usando voz (texto recibido y teléfono) y envía confirmación por SMS.
    """
    async for session in get_session():
        payload = TicketCreate(
            TicketNumber=f"CALL-{phone[-4:]}",
            ShortDescription=text[:80],
            CreatedBy="IVR",
            Status="Nuevo",
        )
        ticket = await create_ticket(payload, session)

        # Embedding inicial
        ticket_dict = ticket.__dict__.copy()
        ticket_dict["attachments_ocr"] = []
        await embed_and_store(
            key=f"ticket:{ticket.id}",
            ticket=ticket_dict,
            ticket_id=ticket.id,
            status=ticket.Status,
        )

        # SMS de confirmación
        tw_sid = os.getenv("TWILIO_ACCOUNT_SID")
        tw_token = os.getenv("TWILIO_AUTH_TOKEN")
        tw_from = os.getenv("TWILIO_FROM_NUMBER")
        try:
            twilio = Client(tw_sid, tw_token)
            twilio.messages.create(
                to=phone,
                from_=tw_from,
                body=f"Ticket {ticket.TicketNumber} creado. ¡Gracias por usar nuestro sistema de soporte!",
            )
        except Exception as e:
            LOG.warning("Error enviando SMS: %s", e)


# ==================================================
# (2) CONSULTA: NÚMERO directo o KNN + campos pedidos
# ==================================================

async def handle_ticket_query(text: str, phone: str) -> str:
    """
    1) Si detecta un número de ticket/folio en el texto, busca DIRECTO por número.
    2) Si no hay número, hace KNN (Redis) y arma respuesta.
    3) Limita la respuesta a los campos pedidos por el usuario; por defecto Status+ShortDescription+Description.
    4) Si el usuario pide “todo” -> devuelve todos los parámetros conocidos.
    """
    LOG.warning("🆕 handle_ticket_query v2 activo")
    LOG.warning("[ECHO] text='%s'", text)

    async for session in get_session():
        LOG.info("[KNN] query='%s'", text)
        requested = parse_requested_fields(text)
        LOG.warning("[FIELDS] requested=%s", requested)

        # -------- 1) Intento directo por NÚMERO --------
        # Acepta formatos con o sin guiones/espacios: INC 250806204037-95 / INC-25080620403795 / 250806204037-95
        digits = "".join(re.findall(r"\d", text))
        if len(digits) >= 6:  # umbral bajo para aceptar números largos
            direct = await search_ticket_by_number(digits)
            if direct:
                t = SimpleNamespace(**direct)
                return format_ticket_reply(t, requested)

        # -------- 2) Fallback: KNN por embeddings --------
        results = await knn_search(text, k=1, session=session)
        LOG.info(
            "[KNN] top=%s score=%s threshold=%s",
            results[0]["ticket"].id if results else None,
            results[0]["score"] if results else None,
            settings.EMBEDDING_SCORE_THRESHOLD,
        )

        if not results:
            return (
                "No encontramos tickets relacionados con tu solicitud. "
                "Por favor verifica el número de ticket o proporciona más detalles."
            )

        best = results[0]
        score = float(best["score"])
        ticket = best["ticket"]

        if score < settings.EMBEDDING_SCORE_THRESHOLD or score < 0.60:
            return format_ticket_reply(ticket, requested)

        return (
            "No encontramos tickets suficientemente relacionados con tu solicitud. "
            "Por favor verifica el número de ticket o proporciona más detalles."
        )


# ===================================
# (3) CONSULTA POR NÚMERO DE TICKET
# ===================================

async def search_ticket_by_number(ticket_number: str) -> Optional[dict]:
    """
    Busca un ticket por su número, comparando solo los dígitos.
    Devuelve un dict con la mayor cantidad de campos útiles para “información completa”.
    """
    async for session in get_session():
        digits_only = "".join(filter(str.isdigit, ticket_number))
        query = select(Ticket).where(
            func.regexp_replace(Ticket.TicketNumber, r"\D", "", "g") == digits_only
        )
        result = await session.execute(query)
        ticket = result.scalar_one_or_none()

        if ticket:
            return {
                "TicketNumber": ticket.TicketNumber,
                "ShortDescription": ticket.ShortDescription,
                "Description": ticket.Description,
                "Status": ticket.Status,
                "Priority": ticket.Priority,
                "Impact": ticket.Impact,
                "Urgency": ticket.Urgency,
                "Severity": ticket.Severity,
                "Category": ticket.Category,
                "Subcategory": ticket.Subcategory,
                "AssignmentGroup": ticket.AssignmentGroup,
                "AssignedTo": ticket.AssignedTo,
                "Company": ticket.Company,
                "Channel": ticket.Channel,
                "Folio": ticket.Folio,
            }
    return None


# ===================================
# (4) SÍNTESIS DE VOZ (no usada en RT)
# ===================================

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
ELEVEN_API_URL = os.getenv("ELEVENLABS_API_URL", "https://api.elevenlabs.io")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
TMP_DIR = os.getenv("TMP_DIR", "./audio_tmp")

async def synthesize_speech(text: str) -> str:
    """
    Convierte texto a voz usando ElevenLabs y devuelve la URL pública del audio generado.

    DEPRECATED:
        Esta función no se utiliza en el flujo de streaming en tiempo real (RT).
        Se mantiene solo para compatibilidad con integraciones previas.

    Args:
        text (str): Texto a convertir a voz.

    Returns:
        str: URL pública del audio generado.
    """
    url = f"{ELEVEN_API_URL}/v1/text-to-speech/{ELEVEN_VOICE_ID}"
    headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
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

    LOG.info(f"Audio generado en: {path}")
    LOG.info("URL del audio para Twilio: %s", f"{PUBLIC_BASE_URL}/audio/{filename}")
    return f"{PUBLIC_BASE_URL}/audio/{filename}"