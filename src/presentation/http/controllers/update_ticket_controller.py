from src.application.contracts.use_cases import UpdateTicket
from src.application.dtos.update_ticket import UpdateTicketInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class UpdateTicketController(Controller):
    def __init__(self, use_case: UpdateTicket) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = UpdateTicketInput(**{**request.params, **request.body})
        try:
            output = await self._use_case.execute(input_dto)
        except ValueError:
            return Response(status_code=404)
        return Response(status_code=200, body=output.ticket.model_dump())
