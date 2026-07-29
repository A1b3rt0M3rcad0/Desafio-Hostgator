from src.application.contracts.repositories import CustomerRepository
from src.application.contracts.use_cases import DeleteCustomer as DeleteCustomerContract
from src.application.dtos.delete_customer import DeleteCustomerInput, DeleteCustomerOutput


class DeleteCustomer(DeleteCustomerContract):
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: DeleteCustomerInput) -> DeleteCustomerOutput:
        await self._repository.delete(input_dto.customer_id)
        return DeleteCustomerOutput(success=True)
