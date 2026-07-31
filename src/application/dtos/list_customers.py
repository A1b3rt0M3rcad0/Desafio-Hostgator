from pydantic import BaseModel

from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import CustomerEntity


class ListCustomersInput(BaseModel):
    cursor: str | None = None
    page_size: int = 20


class ListCustomersOutput(BaseModel):
    page: CursorPage[CustomerEntity]
