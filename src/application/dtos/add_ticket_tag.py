from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import TicketTagEntity


class AddTicketTagInput(BaseModel):
    ticket_id: UUID
    tag_id: UUID


class AddTicketTagOutput(BaseModel):
    ticket_tag: TicketTagEntity
