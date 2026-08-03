from src.application.contracts.ingestion_control import (
    GetIngestionControl as GetIngestionControlContract,
    UpdateIngestionControl as UpdateIngestionControlContract,
)
from src.application.contracts.repositories import TicketRepository
from src.application.dtos.ingestion_control import (
    GetIngestionControlOutput,
    UpdateIngestionControlInput,
    UpdateIngestionControlOutput,
)


class GetIngestionControl(GetIngestionControlContract):
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self) -> GetIngestionControlOutput:
        control = await self._repository.get_ingestion_control()
        return GetIngestionControlOutput(control=control)


class UpdateIngestionControl(UpdateIngestionControlContract):
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        input_dto: UpdateIngestionControlInput,
    ) -> UpdateIngestionControlOutput:
        control = await self._repository.set_ingestion_enabled(input_dto.enabled)
        return UpdateIngestionControlOutput(control=control)
