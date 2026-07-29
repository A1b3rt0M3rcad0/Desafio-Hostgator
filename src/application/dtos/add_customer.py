from pydantic import BaseModel

from src.domain.entities import CustomerEntity


class AddCustomerInput(BaseModel):
    external_requester_id: int
    requester_name: str
    requester_email: str


class AddCustomerOutput(BaseModel):
    customer: CustomerEntity
