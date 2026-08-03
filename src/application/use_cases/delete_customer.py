
from src.application.contracts.repositories import CustomerRepository
from src.application.contracts.use_cases import DeleteCustomer as DeleteCustomerContract
from src.application.dtos.delete_customer import DeleteCustomerInput, DeleteCustomerOutput


class DeleteCustomer(DeleteCustomerContract):
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: DeleteCustomerInput) -> DeleteCustomerOutput:
        customer = await self._repository.get(input_dto.customer_id)
        if customer is None:
            raise ValueError(f"Customer {input_dto.customer_id} not found")
        customer.is_monitored = False
        await self._repository.update(customer)
        return DeleteCustomerOutput(success=True)
