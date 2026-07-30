from src.application.contracts.use_cases import GetTicket
from src.application.dtos.get_ticket import GetTicketInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class GetTicketController(Controller):
    def __init__(self, use_case: GetTicket) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = GetTicketInput(**request.params)
        output = await self._use_case.execute(input_dto)
        if output.ticket is None:
            return Response(status_code=404)
        return Response(status_code=200, body=output.ticket.model_dump())
