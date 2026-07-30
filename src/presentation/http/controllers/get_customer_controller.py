from src.application.contracts.use_cases import GetCustomer
from src.application.dtos.get_customer import GetCustomerInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class GetCustomerController(Controller):
    def __init__(self, use_case: GetCustomer) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = GetCustomerInput(**request.params)
        output = await self._use_case.execute(input_dto)
        if output.customer is None:
            return Response(status_code=404)
        return Response(status_code=200, body=output.customer.model_dump())
