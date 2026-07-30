from src.application.contracts.use_cases import UpdateSatisfactionRating
from src.application.dtos.update_satisfaction_rating import UpdateSatisfactionRatingInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class UpdateSatisfactionRatingController(Controller):
    def __init__(self, use_case: UpdateSatisfactionRating) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = UpdateSatisfactionRatingInput(**{**request.params, **request.body})
        try:
            output = await self._use_case.execute(input_dto)
        except ValueError:
            return Response(status_code=404)
        return Response(status_code=200, body=output.satisfaction_rating.model_dump())
