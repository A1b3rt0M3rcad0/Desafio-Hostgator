from src.application.contracts.repositories import UserRepository
from src.application.contracts.use_cases import ListUsers as ListUsersContract
from src.application.dtos.list_users import ListUsersInput, ListUsersOutput


class ListUsers(ListUsersContract):
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: ListUsersInput) -> ListUsersOutput:
        page = await self._repository.page(input_dto.cursor, input_dto.page_size)
        return ListUsersOutput(page=page)
