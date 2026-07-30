from src.application.contracts.use_cases import AddCustomer
from src.application.dtos.add_customer import AddCustomerInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class AddCustomerController(Controller):
    def __init__(self, use_case: AddCustomer) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = AddCustomerInput(**request.body)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=201, body=output.customer.model_dump())
