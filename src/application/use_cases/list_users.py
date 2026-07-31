from src.application.contracts.repositories import UserRepository
from src.application.contracts.use_cases import ListUsers as ListUsersContract
from src.application.dtos.auth import UserView
from src.application.dtos.cursor_page import CursorPage
from src.application.dtos.list_users import ListUsersInput, ListUsersOutput


class ListUsers(ListUsersContract):
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: ListUsersInput) -> ListUsersOutput:
        page = await self._repository.page(input_dto.cursor, input_dto.page_size)
        public_page = CursorPage[UserView](
            items=[UserView.model_validate(user) for user in page.items],
            next_cursor=page.next_cursor,
            previous_cursor=page.previous_cursor,
            has_next=page.has_next,
            has_previous=page.has_previous,
        )
        return ListUsersOutput(page=public_page)
