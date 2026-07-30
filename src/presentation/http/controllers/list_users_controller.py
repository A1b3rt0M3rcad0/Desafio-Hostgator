from src.application.contracts.use_cases import ListUsers
from src.application.dtos.list_users import ListUsersInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class ListUsersController(Controller):
    def __init__(self, use_case: ListUsers) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = ListUsersInput(**request.query)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=200, body=output.page.model_dump())
