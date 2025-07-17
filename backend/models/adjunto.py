# backend/models/adjunto.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.database.connection import Base

class Adjunto(Base):
    __tablename__ = "adjuntos"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    filename = Column(String)
    url = Column(String)
    uploaded_at = Column(DateTime)
    # relación opcional:
    ticket = relationship("Ticket", back_populates="adjuntos")
