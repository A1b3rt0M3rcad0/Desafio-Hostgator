
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.domain.entities import CustomerEntity


class UpdateCustomerInput(BaseModel):
    customer_id: UUID
    external_requester_id: int | None = Field(default=None, gt=0)
    requester_name: str | None = None
    requester_email: str | None = None

    @field_validator("requester_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("requester_name cannot be empty")
        return normalized

    @field_validator("requester_email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("requester_email must be valid")
        return normalized


class UpdateCustomerOutput(BaseModel):
    customer: CustomerEntity
