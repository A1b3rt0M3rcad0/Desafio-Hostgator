from src.application.contracts.repositories import TagRepository
from src.application.contracts.use_cases import DeleteTag as DeleteTagContract
from src.application.dtos.delete_tag import DeleteTagInput, DeleteTagOutput


class DeleteTag(DeleteTagContract):
    def __init__(self, repository: TagRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: DeleteTagInput) -> DeleteTagOutput:
        await self._repository.delete(input_dto.tag_id)
        return DeleteTagOutput(success=True)
