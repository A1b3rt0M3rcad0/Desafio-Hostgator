from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import SatisfactionRatingEntity


class GetSatisfactionRatingInput(BaseModel):
    satisfaction_rating_id: UUID


class GetSatisfactionRatingOutput(BaseModel):
    satisfaction_rating: SatisfactionRatingEntity | None
