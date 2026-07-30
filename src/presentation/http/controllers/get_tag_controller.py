from src.application.contracts.use_cases import GetTag
from src.application.dtos.get_tag import GetTagInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class GetTagController(Controller):
    def __init__(self, use_case: GetTag) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = GetTagInput(**request.params)
        output = await self._use_case.execute(input_dto)
        if output.tag is None:
            return Response(status_code=404)
        return Response(status_code=200, body=output.tag.model_dump())
