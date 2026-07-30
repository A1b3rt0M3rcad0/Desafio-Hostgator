from src.application.contracts.use_cases import AddTicketTag
from src.application.dtos.add_ticket_tag import AddTicketTagInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class AddTicketTagController(Controller):
    def __init__(self, use_case: AddTicketTag) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = AddTicketTagInput(**request.body)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=201, body=output.ticket_tag.model_dump())
