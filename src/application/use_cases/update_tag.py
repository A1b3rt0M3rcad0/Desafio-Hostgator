from src.application.contracts.repositories import TagRepository
from src.application.contracts.use_cases import UpdateTag as UpdateTagContract
from src.application.dtos.update_tag import UpdateTagInput, UpdateTagOutput


class UpdateTag(UpdateTagContract):
    def __init__(self, repository: TagRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: UpdateTagInput) -> UpdateTagOutput:
        entity = await self._repository.get(input_dto.tag_id)
        if not entity:
            raise ValueError(f"Tag {input_dto.tag_id} not found")
        update_data = input_dto.model_dump(exclude={"tag_id"}, exclude_none=True)
        for field, value in update_data.items():
            setattr(entity, field, value)
        await self._repository.update(entity)
        return UpdateTagOutput(tag=entity)
