from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import TicketEntity


class GetTicketInput(BaseModel):
    ticket_id: UUID


class GetTicketOutput(BaseModel):
    ticket: TicketEntity | None
