from uuid import UUID

from pydantic import BaseModel

from src.domain.entities import CustomerEntity


class GetCustomerInput(BaseModel):
    customer_id: UUID


class GetCustomerOutput(BaseModel):
    customer: CustomerEntity | None
