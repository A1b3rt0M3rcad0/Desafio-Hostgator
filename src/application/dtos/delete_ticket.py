from uuid import UUID

from pydantic import BaseModel


class DeleteTicketInput(BaseModel):
    ticket_id: UUID


class DeleteTicketOutput(BaseModel):
    success: bool
