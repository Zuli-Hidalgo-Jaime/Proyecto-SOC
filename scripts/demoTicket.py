import sys
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from backend.database.models import Base, Ticket, Embedding
from datetime import datetime
from backend.config.settings import get_settings 

# URL de conexión desde settings
DATABASE_URL = get_settings().DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        # Cambiar el TicketNumber para evitar duplicados
        ticket = Ticket(
            TicketNumber="TKT-998", 
            ShortDescription="No funciona el VPN",
            CreatedBy="Zuli",
            Status="Nuevo"
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)

        # Crear embedding dummy
        embedding = Embedding(
            ticket_id=ticket.id,
            vector="[0.1,0.2,0.3]",
            created_at=datetime.utcnow()
        )
        session.add(embedding)
        await session.commit()

        # Consulta el ticket y carga embeddings con selectinload (asincrónico)
        from sqlalchemy.future import select
        result = await session.execute(
            select(Ticket).options(selectinload(Ticket.embeddings)).where(Ticket.id == ticket.id)
        )
        ticket_obj = result.scalars().first()
        print(f"Ticket recuperado: {ticket_obj.TicketNumber}")
        if ticket_obj.embeddings:
            for emb in ticket_obj.embeddings:
                print(f"Embedding vector: {emb.vector}")
        else:
            print("No hay embeddings para este ticket.")

if __name__ == "__main__":
    asyncio.run(main())

