from src.application.contracts.repositories import CustomerRepository
from src.application.contracts.use_cases import AddCustomer as AddCustomerContract
from src.application.dtos.add_customer import AddCustomerInput, AddCustomerOutput
from src.domain.entities import CustomerEntity


class AddCustomer(AddCustomerContract):
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: AddCustomerInput) -> AddCustomerOutput:
        entity = CustomerEntity(**input_dto.model_dump())
        await self._repository.add(entity)
        return AddCustomerOutput(customer=entity)
