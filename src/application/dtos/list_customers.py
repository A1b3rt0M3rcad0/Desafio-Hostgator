from pydantic import BaseModel

from src.domain.entities import CustomerEntity
from src.domain.objects import CursorPage


class ListCustomersInput(BaseModel):
    cursor: str | None = None
    page_size: int = 20


class ListCustomersOutput(BaseModel):
    page: CursorPage[CustomerEntity]
