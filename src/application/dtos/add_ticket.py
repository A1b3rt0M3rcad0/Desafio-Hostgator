from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import TicketEntity, TicketStatus, TicketPriority


class AddTicketInput(BaseModel):
    customer_id: UUID
    external_ticket_id: int
    subject: str
    description: str
    first_response_at: datetime | None = None
    status: TicketStatus
    priority: TicketPriority
    assignee_external_id: int | None = None
    assignee_name: str | None = None
    source_created_at: datetime
    source_updated_at: datetime


class AddTicketOutput(BaseModel):
    ticket: TicketEntity
