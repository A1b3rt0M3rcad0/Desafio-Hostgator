from uuid import UUID

from pydantic import BaseModel


class DeleteCustomerInput(BaseModel):
    customer_id: UUID


class DeleteCustomerOutput(BaseModel):
    success: bool
