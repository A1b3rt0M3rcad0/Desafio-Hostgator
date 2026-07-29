from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import SatisfactionRatingEntity, SatisfactionScore


class UpdateSatisfactionRatingInput(BaseModel):
    satisfaction_rating_id: UUID
    ticket_id: UUID | None = None
    score: SatisfactionScore | None = None
    offered_at: datetime | None = None
    rated_at: datetime | None = None
    comment: str | None = None


class UpdateSatisfactionRatingOutput(BaseModel):
    satisfaction_rating: SatisfactionRatingEntity
