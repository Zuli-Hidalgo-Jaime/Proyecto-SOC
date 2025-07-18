# backend/routes/tickets.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.auth.basic_auth import verify_basic_auth
from backend.database.connection import get_session
from backend.database.models import Ticket
from backend.embeddings.service import embed_and_store
from backend.schemas.ticket import TicketCreate, TicketUpdate, TicketOut

import logging
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
router = APIRouter(
    prefix="/api/tickets",
    tags=["tickets"]
)
# ---------------------------------------------------------------------------


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║ 1. LISTAR TICKETS                                                      ║
# ╚═════════════════════════════════════════════════════════════════════════╝
@router.get(
    "/", 
    response_model=List[TicketOut],
    response_model_by_alias=True,
    summary="Listar tickets"
)
async def list_tickets(session: AsyncSession = Depends(get_session)):
    logger.info("Solicitud recibida: listar tickets")
    result = await session.execute(select(Ticket))
    tickets = result.scalars().all()
    logger.info("Se encontraron %s tickets", len(tickets))
    # ─▶ devolvemos objetos SQLAlchemy; FastAPI + Pydantic hacen la magia
    return tickets


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║ 2. OBTENER TICKET POR ID                                               ║
# ╚═════════════════════════════════════════════════════════════════════════╝
@router.get(
    "/{ticket_id}",
    response_model=TicketOut,
    response_model_by_alias=True,
    summary="Consultar ticket por ID"
)
async def get_ticket(ticket_id: int, session: AsyncSession = Depends(get_session)):
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║ 3. CREAR TICKET                                                        ║
# ╚═════════════════════════════════════════════════════════════════════════╝
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
    #auth: None = Depends(verify_basic_auth)
):
    # 1️⃣  Genera TicketNumber si el cliente no envía uno
    import datetime, secrets
    ticket_number = (
        ticket.ticket_number
        or f"INC-{datetime.datetime.utcnow().strftime('%y%m%d%H%M%S')}-{secrets.randbelow(100)}"
    )

    # 2️⃣  Crea la instancia SQLAlchemy (usa snake_case del modelo)
    new_ticket = Ticket(
        TicketNumber     = ticket_number,
        ShortDescription = ticket.short_description,
        CreatedBy        = ticket.created_by,
        Company          = ticket.company,
        ReportedBy       = ticket.reported_by,
        FirstCategory    = ticket.category,
        FirstSubcategory = ticket.subcategory,
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

    # 3️⃣  Guarda en BD
    session.add(new_ticket)
    await session.commit()
    await session.refresh(new_ticket)

    # 4️⃣  Opcional: genera embedding
    try:
        await embed_and_store(
            key       = f"ticket:{new_ticket.id}",
            text      = new_ticket.ShortDescription,
            ticket_id = new_ticket.id,
            status    = new_ticket.Status
        )
    except Exception as e:
        logger.error("Embedding error: %s", e)

    return new_ticket

# ╔═════════════════════════════════════════════════════════════════════════╗
# ║ 4. ACTUALIZAR TICKET                                                   ║
# ╚═════════════════════════════════════════════════════════════════════════╝
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
    db_ticket = await session.get(Ticket, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    # Sólo actualizamos campos presentes en el payload
    update_data = payload.dict(exclude_unset=True, by_alias=True)
    for field, value in update_data.items():
        # Asegúrate de que el nombre exista en el modelo SQLAlchemy
        setattr(db_ticket, field, value)

    await session.commit()
    await session.refresh(db_ticket)
    return db_ticket


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║ 5. ELIMINAR TICKET                                                     ║
# ╚═════════════════════════════════════════════════════════════════════════╝
@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar ticket"
)
async def delete_ticket(ticket_id: int, session: AsyncSession = Depends(get_session)):
    db_ticket = await session.get(Ticket, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    await session.delete(db_ticket)
    await session.commit()
    return  # 204 → sin cuerpo
