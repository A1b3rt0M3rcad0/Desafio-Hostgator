from src.application.contracts.use_cases import DeleteTag
from src.application.dtos.delete_tag import DeleteTagInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class DeleteTagController(Controller):
    def __init__(self, use_case: DeleteTag) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = DeleteTagInput(**request.params)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=200, body=output.model_dump())
