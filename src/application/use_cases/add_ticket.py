from src.application.contracts.repositories import TicketRepository
from src.application.contracts.use_cases import AddTicket as AddTicketContract
from src.application.dtos.add_ticket import AddTicketInput, AddTicketOutput
from src.domain.entities import TicketEntity


class AddTicket(AddTicketContract):
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: AddTicketInput) -> AddTicketOutput:
        entity = TicketEntity(**input_dto.model_dump())
        await self._repository.add(entity)
        return AddTicketOutput(ticket=entity)
