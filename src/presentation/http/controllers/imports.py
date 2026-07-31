from typing import Any

from src.application.dtos.imports import SyncTicketsInput
from src.application.use_cases.imports import SyncTicketsFromMock
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class SyncTicketsFromMockController(Controller):
    def __init__(self, use_case: SyncTicketsFromMock) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        payload: Any = request.body
        if isinstance(payload, list):
            normalized = {"tickets": payload}
        elif isinstance(payload, dict) and isinstance(payload.get("tickets"), list):
            normalized = {"tickets": payload["tickets"]}
        elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
            normalized = {"tickets": payload["data"]}
        else:
            normalized = payload or {}
        output = await self._use_case.execute(SyncTicketsInput(**normalized))
        return Response(status_code=200, body=output.model_dump(mode="json"))
