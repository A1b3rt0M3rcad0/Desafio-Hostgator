from src.application.contracts.repositories import TagRepository
from src.application.contracts.use_cases import ListTags as ListTagsContract
from src.application.dtos.list_tags import ListTagsInput, ListTagsOutput


class ListTags(ListTagsContract):
    def __init__(self, repository: TagRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: ListTagsInput) -> ListTagsOutput:
        page = await self._repository.page(input_dto.cursor, input_dto.page_size)
        return ListTagsOutput(page=page)
