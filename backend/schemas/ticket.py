# backend/schemas/ticket.py
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. MODELO BASE – todos los campos con alias en PascalCase
# ---------------------------------------------------------------------------
class TicketBase(BaseModel):
    # ─── Identificadores ────────────────────────────
    ticket_number: Optional[str] = Field(None, alias="TicketNumber")
    folio:         Optional[str] = Field(None, alias="Folio")

    # ─── Descripción ────────────────────────────────
    short_description: str           = Field(...,  alias="ShortDescription")
    description:       Optional[str] = Field(None, alias="Description")

    # ─── Metadatos ──────────────────────────────────
    created_by: str                 = Field(..., alias="CreatedBy")
    company:     Optional[str]      = Field(None, alias="Company")
    reported_by: Optional[str]      = Field(None, alias="ReportedBy")

    # ─── Clasificación ─────────────────────────────
    category:    Optional[str] = Field(None, alias="Category")
    subcategory: Optional[str] = Field(None, alias="Subcategory")
    severity:    Optional[str] = Field(None, alias="Severity")
    impact:      Optional[str] = Field(None, alias="Impact")
    urgency:     Optional[str] = Field(None, alias="Urgency")
    priority:    Optional[str] = Field(None, alias="Priority")

    # ─── Flujo / proceso ───────────────────────────
    status:    str           = Field(default="Nuevo", alias="Status")
    workflow:  Optional[str] = Field(None, alias="Workflow")
    channel:   Optional[str] = Field(default="Web", alias="Channel")

    # ─── Asignación ────────────────────────────────
    assignment_group: Optional[str] = Field(None, alias="AssignmentGroup")
    assigned_to:      Optional[str] = Field(None, alias="AssignedTo")

    # ─── Fechas solo en respuestas ─────────────────
    created_at: Optional[datetime] = Field(None, alias="CreatedAt")
    updated_at: Optional[datetime] = Field(None, alias="UpdatedAt")

    # Configuración para Pydantic v2
    model_config = {
        "populate_by_name": True,   # permite usar snake_case o alias al crear el modelo
        "from_attributes":  True,   # permite convertir objetos SQLAlchemy (orm_mode)
    }


# ---------------------------------------------------------------------------
# 2. MODELOS PARA OPERACIONES CRUD
# ---------------------------------------------------------------------------
class TicketCreate(TicketBase):
    """
    Campos requeridos al CREAR.
    (Si quieres que TicketNumber/Folio los genere el backend,
     déjalos Optional en TicketBase – así el cliente puede omitirlos.)
    """
    pass


class TicketUpdate(TicketBase):
    """
    Para PUT / PATCH. Todos opcionales → el cliente envía solo lo que cambia.
    """
    short_description: Optional[str] = Field(None, alias="ShortDescription")
    description: Optional[str] = Field(None, alias="Description")
    # … deja todos los campos como Optional si deseas PATCH flexible


class TicketOut(TicketBase):
    """
    Modelo de RESPUESTA con campos de solo lectura extras.
    """
    id: int
    created_at: Optional[datetime] = Field(None, alias="CreatedAt")
    updated_at: Optional[datetime] = Field(None, alias="UpdatedAt")


