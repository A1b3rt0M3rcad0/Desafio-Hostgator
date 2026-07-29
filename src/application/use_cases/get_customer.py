from src.application.contracts.repositories import CustomerRepository
from src.application.contracts.use_cases import GetCustomer as GetCustomerContract
from src.application.dtos.get_customer import GetCustomerInput, GetCustomerOutput


class GetCustomer(GetCustomerContract):
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: GetCustomerInput) -> GetCustomerOutput:
        entity = await self._repository.get(input_dto.customer_id)
        return GetCustomerOutput(customer=entity)
