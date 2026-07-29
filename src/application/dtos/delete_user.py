from uuid import UUID

from pydantic import BaseModel


class DeleteUserInput(BaseModel):
    user_id: UUID


class DeleteUserOutput(BaseModel):
    success: bool
