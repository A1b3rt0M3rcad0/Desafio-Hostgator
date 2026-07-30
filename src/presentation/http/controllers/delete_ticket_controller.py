from src.application.contracts.use_cases import DeleteTicket
from src.application.dtos.delete_ticket import DeleteTicketInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class DeleteTicketController(Controller):
    def __init__(self, use_case: DeleteTicket) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = DeleteTicketInput(**request.params)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=200, body=output.model_dump())
