from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import SatisfactionRatingEntity, SatisfactionScore


class AddSatisfactionRatingInput(BaseModel):
    ticket_id: UUID
    score: SatisfactionScore
    offered_at: datetime | None = None
    rated_at: datetime | None = None
    comment: str = ""


class AddSatisfactionRatingOutput(BaseModel):
    satisfaction_rating: SatisfactionRatingEntity
