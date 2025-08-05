# backend/routes/tickets.py
"""
Rutas para gestión de tickets, historial y embeddings.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database.models import Attachment, Ticket, TicketHistory
from backend.database.connection import get_session
from backend.embeddings.service import embed_and_store
from backend.schemas.ticket import TicketCreate, TicketUpdate, TicketOut
from backend.utils.redis_client import redis_client

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/tickets",
    tags=["tickets"]
)

@router.get(
    "/", 
    response_model=List[TicketOut],
    response_model_by_alias=True,
    summary="Listar tickets"
)
async def list_tickets(session: AsyncSession = Depends(get_session)):
    """
    Devuelve la lista de tickets.
    """
    logger.info("Solicitud recibida: listar tickets")
    result = await session.execute(select(Ticket))
    tickets = result.scalars().all()
    logger.info("Se encontraron %s tickets", len(tickets))
    return tickets

@router.get(
    "/{ticket_id}",
    response_model=TicketOut,
    response_model_by_alias=True,
    summary="Consultar ticket por ID"
)
async def get_ticket(ticket_id: int, session: AsyncSession = Depends(get_session)):
    """
    Devuelve el ticket por ID.
    """
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket

@router.post(
    "/",
    response_model=TicketOut,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    summary="Crear ticket"
)
async def create_ticket(
    ticket: TicketCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Crea un nuevo ticket y genera su embedding.
    """
    import datetime, secrets
    ticket_number = (
        ticket.ticket_number
        or f"INC-{datetime.datetime.utcnow().strftime('%y%m%d%H%M%S')}-{secrets.randbelow(100)}"
    )

    new_ticket = Ticket(
        TicketNumber     = ticket_number,
        ShortDescription = ticket.short_description,
        CreatedBy        = ticket.created_by,
        Company          = ticket.company,
        ReportedBy       = ticket.reported_by,
        Category         = ticket.category,
        Subcategory      = ticket.subcategory,
        Severity         = ticket.severity,
        Folio            = ticket.folio,
        Description      = ticket.description,
        Channel          = ticket.channel,
        Status           = ticket.status,
        Workflow         = ticket.workflow,
        Impact           = ticket.impact,
        Urgency          = ticket.urgency,
        Priority         = ticket.priority,
        AssignmentGroup  = ticket.assignment_group,
        AssignedTo       = ticket.assigned_to,
    )

    session.add(new_ticket)
    await session.commit()
    await session.refresh(new_ticket)

    # Embedding inicial vacío (sin adjuntos)
    try:
        ticket_dict = new_ticket.__dict__.copy()
        ticket_dict["attachments_ocr"] = []
        await embed_and_store(
            key=f"ticket:{new_ticket.id}",
            ticket=ticket_dict,
            ticket_id=new_ticket.id,
            status=new_ticket.Status
        )
    except Exception as e:
        logger.error("Embedding error: %s", e)

    return new_ticket

@router.put(
    "/{ticket_id}",
    response_model=TicketOut,
    response_model_by_alias=True,
    summary="Actualizar ticket"
)
async def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    session: AsyncSession = Depends(get_session)
):
    """
    Actualiza los campos de un ticket y guarda cambios en el historial.
    También regenera el embedding.
    """
    db_ticket = await session.get(Ticket, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    update_data = payload.dict(exclude_unset=True, by_alias=True)
    for field, value in update_data.items():
        old_value = getattr(db_ticket, field)
        if value != old_value:
            history = TicketHistory(
                ticket_id=db_ticket.id,
                field_changed=field,
                old_value=str(old_value) if old_value is not None else '',
                new_value=str(value) if value is not None else '',
                changed_by="usuario",  # Puedes cambiarlo por usuario real
            )
            session.add(history)
        setattr(db_ticket, field, value)

    await session.commit()
    await session.refresh(db_ticket)

    # Regenerar embedding con OCR si hay adjuntos
    try:
        result = await session.execute(
            select(Attachment).where(Attachment.ticket_id == ticket_id)
        )
        attachments = result.scalars().all()
        ocr_texts = [att.ocr_content for att in attachments if att.ocr_content]
        ticket_dict = db_ticket.__dict__.copy()
        ticket_dict["attachments_ocr"] = ocr_texts

        await embed_and_store(
            key=f"ticket:{db_ticket.id}",
            ticket=ticket_dict,
            ticket_id=db_ticket.id,
            status=db_ticket.Status
        )
    except Exception as e:
        logging.warning(f"No se pudo regenerar el embedding en Redis para ticket editado {ticket_id}: {e}")

    return db_ticket

@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar ticket"
)
async def delete_ticket(ticket_id: int, session: AsyncSession = Depends(get_session)):
    """
    Elimina un ticket y su embedding de Redis.
    """
    db_ticket = await session.get(Ticket, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    await session.delete(db_ticket)
    await session.commit()

    try:
        redis_key = f"emb:ticket:{ticket_id}"
        redis_client.delete(redis_key)
    except Exception as e:
        logger.warning(f"No se pudo eliminar el embedding en Redis para {redis_key}: {e}")

    return

@router.get(
    "/{ticket_id}/history",
    summary="Consultar historial de cambios de un ticket"
)
async def get_ticket_history(ticket_id: int, session: AsyncSession = Depends(get_session)):
    """
    Devuelve el historial de cambios del ticket.
    """
    result = await session.execute(
        select(TicketHistory)
        .where(TicketHistory.ticket_id == ticket_id)
        .order_by(TicketHistory.changed_at.desc())
    )
    history = result.scalars().all()
    return [
        {
            "field_changed": h.field_changed,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "changed_by": h.changed_by,
            "changed_at": h.changed_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for h in history
    ]
