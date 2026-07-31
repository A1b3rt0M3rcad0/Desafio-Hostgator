from src.application.contracts.analytics import TicketImportRepository
from src.application.dtos.imports import SyncTicketsInput, SyncTicketsOutput


class SyncTicketsFromMock:
    def __init__(self, repository: TicketImportRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: SyncTicketsInput) -> SyncTicketsOutput:
        return await self._repository.sync(input_dto.tickets)
