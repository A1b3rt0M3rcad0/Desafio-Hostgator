from src.application.contracts.use_cases import UpdateTag
from src.application.dtos.update_tag import UpdateTagInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class UpdateTagController(Controller):
    def __init__(self, use_case: UpdateTag) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = UpdateTagInput(**{**request.params, **request.body})
        try:
            output = await self._use_case.execute(input_dto)
        except ValueError:
            return Response(status_code=404)
        return Response(status_code=200, body=output.tag.model_dump())
