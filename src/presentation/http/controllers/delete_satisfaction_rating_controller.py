from src.application.contracts.use_cases import DeleteSatisfactionRating
from src.application.dtos.delete_satisfaction_rating import DeleteSatisfactionRatingInput
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class DeleteSatisfactionRatingController(Controller):
    def __init__(self, use_case: DeleteSatisfactionRating) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        input_dto = DeleteSatisfactionRatingInput(**request.params)
        output = await self._use_case.execute(input_dto)
        return Response(status_code=200, body=output.model_dump())
