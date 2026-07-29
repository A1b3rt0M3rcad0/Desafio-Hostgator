from pydantic import BaseModel

from src.domain.entities import TicketEntity
from src.domain.objects import CursorPage


class ListTicketsInput(BaseModel):
    cursor: str | None = None
    page_size: int = 20


class ListTicketsOutput(BaseModel):
    page: CursorPage[TicketEntity]
