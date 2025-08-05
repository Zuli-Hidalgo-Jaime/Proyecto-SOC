# backend/schemas/ticket.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TicketBase(BaseModel):
    """Modelo base para tickets, con alias PascalCase para integración fácil con frontend/backend."""
    ticket_number: Optional[str] = Field(None, alias="TicketNumber")
    folio: Optional[str] = Field(None, alias="Folio")
    short_description: str = Field(..., alias="ShortDescription")
    description: Optional[str] = Field(None, alias="Description")
    created_by: str = Field(..., alias="CreatedBy")
    company: Optional[str] = Field(None, alias="Company")
    reported_by: Optional[str] = Field(None, alias="ReportedBy")
    category: Optional[str] = Field(None, alias="Category")
    subcategory: Optional[str] = Field(None, alias="Subcategory")
    severity: Optional[str] = Field(None, alias="Severity")
    impact: Optional[str] = Field(None, alias="Impact")
    urgency: Optional[str] = Field(None, alias="Urgency")
    priority: Optional[str] = Field(None, alias="Priority")
    status: str = Field(default="Nuevo", alias="Status")
    workflow: Optional[str] = Field(None, alias="Workflow")
    channel: Optional[str] = Field(default="Web", alias="Channel")
    assignment_group: Optional[str] = Field(None, alias="AssignmentGroup")
    assigned_to: Optional[str] = Field(None, alias="AssignedTo")
    created_at: Optional[datetime] = Field(None, alias="CreatedAt")
    updated_at: Optional[datetime] = Field(None, alias="UpdatedAt")
    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }

class TicketCreate(TicketBase):
    """Modelo para crear tickets (POST)."""
    pass

class TicketUpdate(TicketBase):
    """Modelo para actualizar tickets (PUT/PATCH)."""
    short_description: Optional[str] = Field(None, alias="ShortDescription")
    description: Optional[str] = Field(None, alias="Description")

class TicketOut(TicketBase):
    """Modelo de respuesta con campos de solo lectura extras."""
    id: int
    created_at: Optional[datetime] = Field(None, alias="CreatedAt")
    updated_at: Optional[datetime] = Field(None, alias="UpdatedAt")
