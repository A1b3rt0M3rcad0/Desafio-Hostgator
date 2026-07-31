from pydantic import BaseModel, Field, field_validator

from src.application.dtos.auth import UserView


class AddUserInput(BaseModel):
    email: str
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("A valid email is required.")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_size(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes.")
        return value


class AddUserOutput(BaseModel):
    user: UserView
