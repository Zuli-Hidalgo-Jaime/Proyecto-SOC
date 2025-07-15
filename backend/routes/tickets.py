from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.auth.basic_auth import verify_basic_auth
from backend.database.models import Ticket
from backend.database.connection import get_session
from backend.embeddings.service import embed_and_store
from backend.schemas.ticket import TicketCreate, TicketOut

import logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", summary="Listar tickets")
async def list_tickets(session: AsyncSession = Depends(get_session)):
    logger.info("Solicitud recibida: listar tickets")
    result = await session.execute(select(Ticket))
    tickets = result.scalars().all()
    logger.info(f"Se encontraron {len(tickets)} tickets")
    return [ 
        {
            "id": t.id,
            "TicketNumber": t.TicketNumber,
            "ShortDescription": t.ShortDescription,
            "Status": t.Status
        } for t in tickets
    ]

@router.get("/{ticket_id}", summary="Consultar ticket por ID")
async def get_ticket(ticket_id: int, session: AsyncSession = Depends(get_session)):
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return {
        "id": ticket.id,
        "TicketNumber": ticket.TicketNumber,
        "ShortDescription": ticket.ShortDescription,
        "Status": ticket.Status
    }

# Crear ticket
@router.post("/", response_model=TicketOut, summary="Crear ticket")
async def create_ticket(ticket: TicketCreate, session: AsyncSession = Depends(get_session), auth=Depends(verify_basic_auth)):
    new_ticket = Ticket(
        TicketNumber=ticket.TicketNumber,
        ShortDescription=ticket.ShortDescription,
        CreatedBy=ticket.CreatedBy,
        Status=ticket.Status
    )
    session.add(new_ticket)
    await session.commit()
    await session.refresh(new_ticket)

    # 2️⃣ generar y guardar embedding (clave: ticket:<id>)
    try:
        await embed_and_store(
            key=f"ticket:{new_ticket.id}",
            text=new_ticket.ShortDescription,
            ticket_id=new_ticket.id,
            status=new_ticket.Status
        )
    except Exception as e:
        logger.error("Embedding error: %s", e)

    return new_ticket

# Actualizar ticket
@router.put("/{ticket_id}", response_model=TicketOut, summary="Actualizar ticket")
async def update_ticket(ticket_id: int, ticket: TicketCreate, session: AsyncSession = Depends(get_session)):
    db_ticket = await session.get(Ticket, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    db_ticket.TicketNumber = ticket.TicketNumber
    db_ticket.ShortDescription = ticket.ShortDescription
    db_ticket.Status = ticket.Status
    await session.commit()
    await session.refresh(db_ticket)
    return db_ticket

# Eliminar ticket
@router.delete("/{ticket_id}", summary="Eliminar ticket")
async def delete_ticket(ticket_id: int, session: AsyncSession = Depends(get_session)):
    db_ticket = await session.get(Ticket, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    await session.delete(db_ticket)
    await session.commit()
    return {"ok": True, "msg": f"Ticket {ticket_id} eliminado"}
