from pydantic import BaseModel

from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import SatisfactionRatingEntity


class ListSatisfactionRatingsInput(BaseModel):
    cursor: str | None = None
    page_size: int = 20


class ListSatisfactionRatingsOutput(BaseModel):
    page: CursorPage[SatisfactionRatingEntity]
