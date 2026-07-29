from src.application.contracts.repositories import TicketRepository
from src.application.contracts.use_cases import GetTicket as GetTicketContract
from src.application.dtos.get_ticket import GetTicketInput, GetTicketOutput


class GetTicket(GetTicketContract):
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: GetTicketInput) -> GetTicketOutput:
        entity = await self._repository.get(input_dto.ticket_id)
        return GetTicketOutput(ticket=entity)
