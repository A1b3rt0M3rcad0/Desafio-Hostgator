from src.application.contracts.ingestion_control import (
    GetIngestionControl,
    UpdateIngestionControl,
)
from src.application.dtos.ingestion_control import UpdateIngestionControlInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class GetIngestionControlController(Controller):
    def __init__(self, use_case: GetIngestionControl) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        del request
        output = await self._use_case.execute()
        return Response(status_code=200, body=output.control.model_dump(mode="json"))


class UpdateIngestionControlController(Controller):
    def __init__(self, use_case: UpdateIngestionControl) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = UpdateIngestionControlInput(**request.body)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=200, body=output.control.model_dump(mode="json"))
