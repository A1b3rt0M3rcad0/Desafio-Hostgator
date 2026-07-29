from src.application.contracts.repositories import CustomerRepository
from src.application.contracts.use_cases import UpdateCustomer as UpdateCustomerContract
from src.application.dtos.update_customer import UpdateCustomerInput, UpdateCustomerOutput


class UpdateCustomer(UpdateCustomerContract):
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: UpdateCustomerInput) -> UpdateCustomerOutput:
        entity = await self._repository.get(input_dto.customer_id)
        if not entity:
            raise ValueError(f"Customer {input_dto.customer_id} not found")
        update_data = input_dto.model_dump(exclude={"customer_id"}, exclude_none=True)
        for field, value in update_data.items():
            setattr(entity, field, value)
        await self._repository.update(entity)
        return UpdateCustomerOutput(customer=entity)
