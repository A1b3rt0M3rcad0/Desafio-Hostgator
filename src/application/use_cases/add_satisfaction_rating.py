from src.application.contracts.repositories import SatisfactionRatingRepository
from src.application.contracts.use_cases import AddSatisfactionRating as AddSatisfactionRatingContract
from src.application.dtos.add_satisfaction_rating import AddSatisfactionRatingInput, AddSatisfactionRatingOutput
from src.domain.entities import SatisfactionRatingEntity


class AddSatisfactionRating(AddSatisfactionRatingContract):
    def __init__(self, repository: SatisfactionRatingRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: AddSatisfactionRatingInput) -> AddSatisfactionRatingOutput:
        entity = SatisfactionRatingEntity(**input_dto.model_dump())
        await self._repository.add(entity)
        return AddSatisfactionRatingOutput(satisfaction_rating=entity)
