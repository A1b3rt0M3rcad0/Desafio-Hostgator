
from pydantic import BaseModel, Field, field_validator

from src.domain.entities import CustomerEntity


class AddCustomerInput(BaseModel):
    external_requester_id: int | None = Field(default=None, gt=0)
    requester_name: str
    requester_email: str

    @field_validator("requester_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("requester_name cannot be empty")
        return normalized

    @field_validator("requester_email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("requester_email must be valid")
        return normalized


class AddCustomerOutput(BaseModel):
    customer: CustomerEntity
