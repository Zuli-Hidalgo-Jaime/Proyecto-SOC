# backend/schemas/ticket.py
from pydantic import BaseModel
from typing import Optional

class TicketCreate(BaseModel):
    TicketNumber: str
    ShortDescription: str
    CreatedBy: str 
    Status: Optional[str] = "Nuevo"

class TicketOut(TicketCreate):
    id: int

    class Config:
        orm_mode = True
