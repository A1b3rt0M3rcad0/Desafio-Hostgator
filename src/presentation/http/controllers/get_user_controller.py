from src.application.contracts.use_cases import GetUser
from src.application.dtos.get_user import GetUserInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class GetUserController(Controller):
    def __init__(self, use_case: GetUser) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = GetUserInput(**request.params)
        output = await self._use_case.execute(input_dto)
        if output.user is None:
            return Response(status_code=404)
        return Response(status_code=200, body=output.user.model_dump())
