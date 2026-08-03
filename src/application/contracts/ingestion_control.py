from abc import ABC, abstractmethod

from src.application.dtos.ingestion_control import (
    GetIngestionControlOutput,
    UpdateIngestionControlInput,
    UpdateIngestionControlOutput,
)


class GetIngestionControl(ABC):
    @abstractmethod
    async def execute(self) -> GetIngestionControlOutput: ...


class UpdateIngestionControl(ABC):
    @abstractmethod
    async def execute(
        self,
        input_dto: UpdateIngestionControlInput,
    ) -> UpdateIngestionControlOutput: ...
