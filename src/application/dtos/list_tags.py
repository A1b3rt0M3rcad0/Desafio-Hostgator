from pydantic import BaseModel

from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import TagEntity


class ListTagsInput(BaseModel):
    cursor: str | None = None
    page_size: int = 20


class ListTagsOutput(BaseModel):
    page: CursorPage[TagEntity]
