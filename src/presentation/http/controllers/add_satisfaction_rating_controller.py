from src.application.contracts.use_cases import AddSatisfactionRating
from src.application.dtos.add_satisfaction_rating import AddSatisfactionRatingInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class AddSatisfactionRatingController(Controller):
    def __init__(self, use_case: AddSatisfactionRating) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = AddSatisfactionRatingInput(**request.body)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=201, body=output.satisfaction_rating.model_dump())
