from src.application.contracts.repositories import TagRepository
from src.application.contracts.use_cases import AddTag as AddTagContract
from src.application.dtos.add_tag import AddTagInput, AddTagOutput
from src.domain.entities import TagEntity


class AddTag(AddTagContract):
    def __init__(self, repository: TagRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: AddTagInput) -> AddTagOutput:
        entity = TagEntity(**input_dto.model_dump())
        await self._repository.add(entity)
        return AddTagOutput(tag=entity)
