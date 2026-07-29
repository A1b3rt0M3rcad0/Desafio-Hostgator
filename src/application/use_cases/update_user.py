from src.application.contracts.repositories import UserRepository
from src.application.contracts.use_cases import UpdateUser as UpdateUserContract
from src.application.dtos.update_user import UpdateUserInput, UpdateUserOutput


class UpdateUser(UpdateUserContract):
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: UpdateUserInput) -> UpdateUserOutput:
        entity = await self._repository.get(input_dto.user_id)
        if not entity:
            raise ValueError(f"User {input_dto.user_id} not found")
        update_data = input_dto.model_dump(exclude={"user_id"}, exclude_none=True)
        for field, value in update_data.items():
            setattr(entity, field, value)
        await self._repository.update(entity)
        return UpdateUserOutput(user=entity)
