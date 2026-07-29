from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import UserEntity


class UpdateUserInput(BaseModel):
    user_id: UUID
    email: str | None = None
    password_hash: bytes | None = None
    refresh_token: str | None = None


class UpdateUserOutput(BaseModel):
    user: UserEntity
