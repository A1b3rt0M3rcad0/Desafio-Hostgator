from src.application.contracts.repositories import TicketTagRepository
from src.application.contracts.use_cases import DeleteTicketTag as DeleteTicketTagContract
from src.application.dtos.delete_ticket_tag import DeleteTicketTagInput, DeleteTicketTagOutput


class DeleteTicketTag(DeleteTicketTagContract):
    def __init__(self, repository: TicketTagRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: DeleteTicketTagInput) -> DeleteTicketTagOutput:
        await self._repository.delete_by_ticket_and_tag(
            input_dto.ticket_id, input_dto.tag_id
        )
        return DeleteTicketTagOutput(success=True)
