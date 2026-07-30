from src.application.contracts.use_cases import AddUser
from src.application.dtos.add_user import AddUserInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class AddUserController(Controller):
    def __init__(self, use_case: AddUser) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = AddUserInput(**request.body)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=201, body=output.user.model_dump())
