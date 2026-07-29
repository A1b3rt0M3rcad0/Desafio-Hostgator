from src.application.contracts.repositories import CustomerRepository
from src.application.contracts.use_cases import ListCustomers as ListCustomersContract
from src.application.dtos.list_customers import ListCustomersInput, ListCustomersOutput


class ListCustomers(ListCustomersContract):
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: ListCustomersInput) -> ListCustomersOutput:
        page = await self._repository.page(input_dto.cursor, input_dto.page_size)
        return ListCustomersOutput(page=page)
