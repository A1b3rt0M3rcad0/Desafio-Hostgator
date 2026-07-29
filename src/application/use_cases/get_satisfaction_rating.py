from src.application.contracts.repositories import SatisfactionRatingRepository
from src.application.contracts.use_cases import GetSatisfactionRating as GetSatisfactionRatingContract
from src.application.dtos.get_satisfaction_rating import GetSatisfactionRatingInput, GetSatisfactionRatingOutput


class GetSatisfactionRating(GetSatisfactionRatingContract):
    def __init__(self, repository: SatisfactionRatingRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: GetSatisfactionRatingInput) -> GetSatisfactionRatingOutput:
        entity = await self._repository.get(input_dto.satisfaction_rating_id)
        return GetSatisfactionRatingOutput(satisfaction_rating=entity)
