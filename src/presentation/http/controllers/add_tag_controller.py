from src.application.contracts.use_cases import AddTag
from src.application.dtos.add_tag import AddTagInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class AddTagController(Controller):
    def __init__(self, use_case: AddTag) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = AddTagInput(**request.body)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=201, body=output.tag.model_dump())
