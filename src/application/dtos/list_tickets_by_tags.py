from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import TicketEntity
from src.domain.objects import CursorPage


class ListTicketsByTagsInput(BaseModel):
    tag_ids: list[UUID]
    cursor: str | None = None
    page_size: int = 20


class ListTicketsByTagsOutput(BaseModel):
    page: CursorPage[TicketEntity]
