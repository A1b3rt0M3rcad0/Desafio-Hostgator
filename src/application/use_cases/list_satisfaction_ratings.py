from src.application.contracts.repositories import SatisfactionRatingRepository
from src.application.contracts.use_cases import ListSatisfactionRatings as ListSatisfactionRatingsContract
from src.application.dtos.list_satisfaction_ratings import ListSatisfactionRatingsInput, ListSatisfactionRatingsOutput


class ListSatisfactionRatings(ListSatisfactionRatingsContract):
    def __init__(self, repository: SatisfactionRatingRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: ListSatisfactionRatingsInput) -> ListSatisfactionRatingsOutput:
        page = await self._repository.page(input_dto.cursor, input_dto.page_size)
        return ListSatisfactionRatingsOutput(page=page)
