from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database.models import Ticket
from backend.database.connection import get_session

router = APIRouter()

@router.get("/", summary="Listar tickets")
async def list_tickets(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Ticket))
    tickets = result.scalars().all()
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
