from src.application.contracts.use_cases import DeleteTicketTag
from src.application.dtos.delete_ticket_tag import DeleteTicketTagInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class DeleteTicketTagController(Controller):
    def __init__(self, use_case: DeleteTicketTag) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = DeleteTicketTagInput(**request.body)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=200, body=output.model_dump())
