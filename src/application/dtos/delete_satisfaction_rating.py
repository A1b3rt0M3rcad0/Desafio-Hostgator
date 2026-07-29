from uuid import UUID

from pydantic import BaseModel


class DeleteSatisfactionRatingInput(BaseModel):
    satisfaction_rating_id: UUID


class DeleteSatisfactionRatingOutput(BaseModel):
    success: bool
