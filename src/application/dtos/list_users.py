from pydantic import BaseModel

from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import UserEntity


class ListUsersInput(BaseModel):
    cursor: str | None = None
    page_size: int = 20


class ListUsersOutput(BaseModel):
    page: CursorPage[UserEntity]
