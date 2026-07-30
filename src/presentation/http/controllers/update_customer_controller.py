from src.application.contracts.use_cases import UpdateCustomer
from src.application.dtos.update_customer import UpdateCustomerInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class UpdateCustomerController(Controller):
    def __init__(self, use_case: UpdateCustomer) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = UpdateCustomerInput(**{**request.params, **request.body})
        try:
            output = await self._use_case.execute(input_dto)
        except ValueError:
            return Response(status_code=404)
        return Response(status_code=200, body=output.customer.model_dump())
