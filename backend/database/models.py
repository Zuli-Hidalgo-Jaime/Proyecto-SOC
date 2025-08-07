#backend/database/models.py
"""
SQLAlchemy models for ProyectoSOC ticketing system.
Define los modelos de Ticket, Attachment, Embedding, User y TicketHistory.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime


Base = declarative_base()

class Ticket(Base):
    """
    Modelo principal para tickets de soporte.
    """
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    TicketNumber = Column(String, unique=True, index=True, nullable=False)
    ShortDescription = Column(String, nullable=False)
    CreatedBy = Column(String, nullable=False)
    Company = Column(String)
    ReportedBy = Column(String)
    Category = Column(String)
    Subcategory = Column(String)
    Severity = Column(String)
    Folio = Column(String)
    Description = Column(Text)
    Channel = Column(String)
    Status = Column(String)
    Workflow = Column(String)
    Impact = Column(String)
    Urgency = Column(String)
    Priority = Column(String)
    AssignmentGroup = Column(String)
    AssignedTo = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    attachments = relationship("Attachment", back_populates="ticket", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="ticket", cascade="all, delete-orphan")

class Attachment(Base):
    """
    Modelo para archivos adjuntos relacionados con un ticket.
    """
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    filename = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    ocr_content = Column(Text)

    ticket = relationship("Ticket", back_populates="attachments")

class Embedding(Base):
    """
    Modelo para embeddings vectoriales asociados a un ticket.
    """
    __tablename__ = "ticket_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    vector = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="embeddings")

class User(Base):
    """
    Modelo para usuarios del sistema.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    full_name = Column(String, nullable=True)   # Nuevo campo
    email = Column(String, unique=True, index=True, nullable=True)  # Nuevo campo
    created_at = Column(DateTime, default=datetime.utcnow)

class TicketHistory(Base):
    """
    Modelo de historial de cambios de tickets.
    """
    __tablename__ = "ticket_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    field_changed = Column(String(64))
    old_value = Column(Text)
    new_value = Column(Text)
    changed_by = Column(String(128))
    changed_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", backref="history")

