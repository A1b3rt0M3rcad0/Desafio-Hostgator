
from src.application.contracts.repositories import CustomerRepository
from src.application.contracts.use_cases import AddCustomer as AddCustomerContract
from src.application.dtos.add_customer import AddCustomerInput, AddCustomerOutput
from src.domain.entities import CustomerEntity


class AddCustomer(AddCustomerContract):
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: AddCustomerInput) -> AddCustomerOutput:
        existing = await self._repository.get_by_email(
            input_dto.requester_email,
            include_unmonitored=True,
        )
        if existing is not None:
            if existing.is_monitored:
                raise ValueError(
                    f"Customer with email {input_dto.requester_email} already exists"
                )
            existing.is_monitored = True
            existing.requester_name = input_dto.requester_name
            if input_dto.external_requester_id is not None:
                existing.external_requester_id = input_dto.external_requester_id
            await self._repository.update(existing)
            return AddCustomerOutput(customer=existing)

        entity = CustomerEntity(
            external_requester_id=input_dto.external_requester_id,
            requester_name=input_dto.requester_name,
            requester_email=input_dto.requester_email,
            is_monitored=True,
        )
        await self._repository.add(entity)
        return AddCustomerOutput(customer=entity)
