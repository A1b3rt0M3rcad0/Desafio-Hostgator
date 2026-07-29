from src.application.contracts.repositories import TicketTagRepository
from src.application.contracts.use_cases import AddTicketTag as AddTicketTagContract
from src.application.dtos.add_ticket_tag import AddTicketTagInput, AddTicketTagOutput
from src.domain.entities import TicketTagEntity


class AddTicketTag(AddTicketTagContract):
    def __init__(self, repository: TicketTagRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: AddTicketTagInput) -> AddTicketTagOutput:
        entity = TicketTagEntity(**input_dto.model_dump())
        await self._repository.add(entity)
        return AddTicketTagOutput(ticket_tag=entity)
