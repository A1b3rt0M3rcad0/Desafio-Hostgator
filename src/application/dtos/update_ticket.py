from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import TicketEntity, TicketStatus, TicketPriority


class UpdateTicketInput(BaseModel):
    ticket_id: UUID
    customer_id: UUID | None = None
    external_ticket_id: int | None = None
    subject: str | None = None
    description: str | None = None
    first_response_at: datetime | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assignee_external_id: int | None = None
    assignee_name: str | None = None
    source_created_at: datetime | None = None
    source_updated_at: datetime | None = None


class UpdateTicketOutput(BaseModel):
    ticket: TicketEntity
