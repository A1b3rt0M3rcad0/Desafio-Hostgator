from src.application.contracts.repositories import TicketRepository
from src.application.contracts.use_cases import ListTicketsByTags as ListTicketsByTagsContract
from src.application.dtos.list_tickets_by_tags import ListTicketsByTagsInput, ListTicketsByTagsOutput


class ListTicketsByTags(ListTicketsByTagsContract):
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: ListTicketsByTagsInput) -> ListTicketsByTagsOutput:
        page = await self._repository.page_by_tag_ids(
            input_dto.tag_ids, input_dto.cursor, input_dto.page_size
        )
        return ListTicketsByTagsOutput(page=page)
