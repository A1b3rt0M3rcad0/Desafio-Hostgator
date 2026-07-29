from src.application.contracts.repositories import TicketRepository
from src.application.contracts.use_cases import DeleteTicket as DeleteTicketContract
from src.application.dtos.delete_ticket import DeleteTicketInput, DeleteTicketOutput


class DeleteTicket(DeleteTicketContract):
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: DeleteTicketInput) -> DeleteTicketOutput:
        await self._repository.delete(input_dto.ticket_id)
        return DeleteTicketOutput(success=True)
