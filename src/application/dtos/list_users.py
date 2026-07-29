from pydantic import BaseModel

from src.domain.entities import UserEntity
from src.domain.objects import CursorPage


class ListUsersInput(BaseModel):
    cursor: str | None = None
    page_size: int = 20


class ListUsersOutput(BaseModel):
    page: CursorPage[UserEntity]
