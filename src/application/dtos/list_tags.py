from pydantic import BaseModel

from src.domain.entities import TagEntity
from src.domain.objects import CursorPage


class ListTagsInput(BaseModel):
    cursor: str | None = None
    page_size: int = 20


class ListTagsOutput(BaseModel):
    page: CursorPage[TagEntity]
