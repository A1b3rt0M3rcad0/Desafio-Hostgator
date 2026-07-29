from src.application.contracts.repositories import SatisfactionRatingRepository
from src.application.contracts.use_cases import DeleteSatisfactionRating as DeleteSatisfactionRatingContract
from src.application.dtos.delete_satisfaction_rating import DeleteSatisfactionRatingInput, DeleteSatisfactionRatingOutput


class DeleteSatisfactionRating(DeleteSatisfactionRatingContract):
    def __init__(self, repository: SatisfactionRatingRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: DeleteSatisfactionRatingInput) -> DeleteSatisfactionRatingOutput:
        await self._repository.delete(input_dto.satisfaction_rating_id)
        return DeleteSatisfactionRatingOutput(success=True)
