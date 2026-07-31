from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.application.dtos.auth import UserView


class UpdateUserInput(BaseModel):
    user_id: UUID
    email: str | None = None
    password: str | None = Field(default=None, min_length=8)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("A valid email is required.")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_size(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes.")
        return value


class UpdateUserOutput(BaseModel):
    user: UserView
