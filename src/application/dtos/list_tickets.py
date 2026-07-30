from pydantic import BaseModel

from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import TicketEntity


class ListTicketsInput(BaseModel):
    cursor: str | None = None
    page_size: int = 20


class ListTicketsOutput(BaseModel):
    page: CursorPage[TicketEntity]
