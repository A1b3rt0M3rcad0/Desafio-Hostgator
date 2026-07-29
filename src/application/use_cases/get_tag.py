from src.application.contracts.repositories import TagRepository
from src.application.contracts.use_cases import GetTag as GetTagContract
from src.application.dtos.get_tag import GetTagInput, GetTagOutput


class GetTag(GetTagContract):
    def __init__(self, repository: TagRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: GetTagInput) -> GetTagOutput:
        entity = await self._repository.get(input_dto.tag_id)
        return GetTagOutput(tag=entity)
