from src.application.contracts.use_cases import DeleteCustomer
from src.application.dtos.delete_customer import DeleteCustomerInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class DeleteCustomerController(Controller):
    def __init__(self, use_case: DeleteCustomer) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = DeleteCustomerInput(**request.params)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=200, body=output.model_dump())
