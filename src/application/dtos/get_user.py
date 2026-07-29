from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import UserEntity


class GetUserInput(BaseModel):
    user_id: UUID


class GetUserOutput(BaseModel):
    user: UserEntity | None
