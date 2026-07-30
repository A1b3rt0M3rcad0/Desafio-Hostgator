from src.application.contracts.use_cases import DeleteUser
from src.application.dtos.delete_user import DeleteUserInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class DeleteUserController(Controller):
    def __init__(self, use_case: DeleteUser) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = DeleteUserInput(**request.params)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=200, body=output.model_dump())
