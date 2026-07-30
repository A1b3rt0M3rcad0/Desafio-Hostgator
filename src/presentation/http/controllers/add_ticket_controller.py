from src.application.contracts.use_cases import AddTicket
from src.application.dtos.add_ticket import AddTicketInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class AddTicketController(Controller):
    def __init__(self, use_case: AddTicket) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = AddTicketInput(**request.body)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=201, body=output.ticket.model_dump())
