from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuthenticateUserInput(BaseModel):
    email: str
    password: str = Field(min_length=8)
    user_agent: str | None = None
    ip_address: str | None = None

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


class AccessTokenClaims(BaseModel):
    user_id: UUID
    session_id: UUID
    token_id: UUID


class AuthenticatedUser(BaseModel):
    id: UUID
    session_id: UUID


class AuthTokensOutput(BaseModel):
    user: UserView
    session_id: UUID
    access_token: str
    refresh_token: str
    access_token_expires_in: int
    refresh_token_expires_in: int


class RefreshAuthSessionInput(BaseModel):
    refresh_token: str


class RefreshAuthSessionResult(BaseModel):
    tokens: AuthTokensOutput | None = None
    error_code: str | None = None


class LogoutAuthSessionInput(BaseModel):
    refresh_token: str | None = None


class LogoutAuthSessionOutput(BaseModel):
    revoked: bool


class LogoutAllAuthSessionsInput(BaseModel):
    user_id: UUID


class LogoutAllAuthSessionsOutput(BaseModel):
    revoked_sessions: int
