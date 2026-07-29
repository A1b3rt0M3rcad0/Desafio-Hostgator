from src.application.contracts.repositories import UserRepository
from src.application.contracts.use_cases import DeleteUser as DeleteUserContract
from src.application.dtos.delete_user import DeleteUserInput, DeleteUserOutput


class DeleteUser(DeleteUserContract):
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: DeleteUserInput) -> DeleteUserOutput:
        await self._repository.delete(input_dto.user_id)
        return DeleteUserOutput(success=True)
