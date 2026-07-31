from src.application.contracts.repositories import UserRepository
from src.application.contracts.use_cases import GetUser as GetUserContract
from src.application.dtos.auth import UserView
from src.application.dtos.get_user import GetUserInput, GetUserOutput


class GetUser(GetUserContract):
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: GetUserInput) -> GetUserOutput:
        entity = await self._repository.get(input_dto.user_id)
        return GetUserOutput(
            user=UserView.model_validate(entity) if entity else None,
        )
