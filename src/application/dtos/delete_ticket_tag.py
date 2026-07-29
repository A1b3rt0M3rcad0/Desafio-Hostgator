from uuid import UUID

from pydantic import BaseModel


class DeleteTicketTagInput(BaseModel):
    ticket_id: UUID
    tag_id: UUID


class DeleteTicketTagOutput(BaseModel):
    success: bool
