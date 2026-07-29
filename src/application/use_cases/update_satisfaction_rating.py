from src.application.contracts.repositories import SatisfactionRatingRepository
from src.application.contracts.use_cases import UpdateSatisfactionRating as UpdateSatisfactionRatingContract
from src.application.dtos.update_satisfaction_rating import UpdateSatisfactionRatingInput, UpdateSatisfactionRatingOutput


class UpdateSatisfactionRating(UpdateSatisfactionRatingContract):
    def __init__(self, repository: SatisfactionRatingRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: UpdateSatisfactionRatingInput) -> UpdateSatisfactionRatingOutput:
        entity = await self._repository.get(input_dto.satisfaction_rating_id)
        if not entity:
            raise ValueError(f"SatisfactionRating {input_dto.satisfaction_rating_id} not found")
        update_data = input_dto.model_dump(exclude={"satisfaction_rating_id"}, exclude_none=True)
        for field, value in update_data.items():
            setattr(entity, field, value)
        await self._repository.update(entity)
        return UpdateSatisfactionRatingOutput(satisfaction_rating=entity)
