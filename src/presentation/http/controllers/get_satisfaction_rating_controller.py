from src.application.contracts.use_cases import GetSatisfactionRating
from src.application.dtos.get_satisfaction_rating import GetSatisfactionRatingInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class GetSatisfactionRatingController(Controller):
    def __init__(self, use_case: GetSatisfactionRating) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = GetSatisfactionRatingInput(**request.params)
        output = await self._use_case.execute(input_dto)
        if output.satisfaction_rating is None:
            return Response(status_code=404)
        return Response(status_code=200, body=output.satisfaction_rating.model_dump())
