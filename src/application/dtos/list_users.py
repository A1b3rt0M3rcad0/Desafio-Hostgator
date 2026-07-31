from pydantic import BaseModel

from src.application.dtos.auth import UserView
from src.application.dtos.cursor_page import CursorPage


class ListUsersInput(BaseModel):
    cursor: str | None = None
    page_size: int = 20


class ListUsersOutput(BaseModel):
    page: CursorPage[UserView]
