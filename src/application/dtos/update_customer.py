from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import CustomerEntity


class UpdateCustomerInput(BaseModel):
    customer_id: UUID
    external_requester_id: int | None = None
    requester_name: str | None = None
    requester_email: str | None = None


class UpdateCustomerOutput(BaseModel):
    customer: CustomerEntity
