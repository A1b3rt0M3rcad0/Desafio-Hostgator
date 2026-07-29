from src.application.contracts.repositories import TicketRepository
from src.application.contracts.use_cases import ListTickets as ListTicketsContract
from src.application.dtos.list_tickets import ListTicketsInput, ListTicketsOutput


class ListTickets(ListTicketsContract):
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: ListTicketsInput) -> ListTicketsOutput:
        page = await self._repository.page(input_dto.cursor, input_dto.page_size)
        return ListTicketsOutput(page=page)
