from pydantic import BaseModel

from src.domain.entities import UserEntity


class AddUserInput(BaseModel):
    email: str
    password_hash: bytes
    refresh_token: str


class AddUserOutput(BaseModel):
    user: UserEntity
