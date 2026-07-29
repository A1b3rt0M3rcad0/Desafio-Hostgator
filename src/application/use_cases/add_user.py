from src.application.contracts.repositories import UserRepository
from src.application.contracts.use_cases import AddUser as AddUserContract
from src.application.dtos.add_user import AddUserInput, AddUserOutput
from src.domain.entities import UserEntity


class AddUser(AddUserContract):
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: AddUserInput) -> AddUserOutput:
        entity = UserEntity(**input_dto.model_dump())
        await self._repository.add(entity)
        return AddUserOutput(user=entity)
