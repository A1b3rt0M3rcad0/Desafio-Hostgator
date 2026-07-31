from uuid import UUID

from pydantic import BaseModel

from src.application.dtos.auth import UserView


class GetUserInput(BaseModel):
    user_id: UUID


class GetUserOutput(BaseModel):
    user: UserView | None
