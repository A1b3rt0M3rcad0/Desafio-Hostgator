from pydantic import BaseModel

from src.domain.entities import SatisfactionRatingEntity
from src.domain.objects import CursorPage


class ListSatisfactionRatingsInput(BaseModel):
    cursor: str | None = None
    page_size: int = 20


class ListSatisfactionRatingsOutput(BaseModel):
    page: CursorPage[SatisfactionRatingEntity]
