from src.application.contracts.ingestion_control import (
    GetIngestionControl as GetIngestionControlContract,
    IngestionControlRepository,
    UpdateIngestionControl as UpdateIngestionControlContract,
)
from src.application.dtos.ingestion_control import (
    GetIngestionControlInput,
    GetIngestionControlOutput,
    UpdateIngestionControlInput,
    UpdateIngestionControlOutput,
)


class GetIngestionControl(GetIngestionControlContract):
    def __init__(self, repository: IngestionControlRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        input_dto: GetIngestionControlInput,
    ) -> GetIngestionControlOutput:
        del input_dto
        return GetIngestionControlOutput(control=await self._repository.get())


class UpdateIngestionControl(UpdateIngestionControlContract):
    def __init__(self, repository: IngestionControlRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        input_dto: UpdateIngestionControlInput,
    ) -> UpdateIngestionControlOutput:
        control = await self._repository.set_enabled(input_dto.enabled)
        return UpdateIngestionControlOutput(control=control)
