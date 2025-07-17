# backend/schemas/adjunto.py
from pydantic import BaseModel
from datetime import datetime

class AdjuntoCreate(BaseModel):
    ticket_id: int
    filename: str

class AdjuntoOut(BaseModel):
    id: int
    ticket_id: int
    filename: str
    url: str
    uploaded_at: datetime

    class Config:
        orm_mode = True
