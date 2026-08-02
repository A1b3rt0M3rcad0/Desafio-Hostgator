from abc import ABC, abstractmethod

from src.application.dtos.ingestion_control import (
    GetIngestionControlInput,
    GetIngestionControlOutput,
    UpdateIngestionControlInput,
    UpdateIngestionControlOutput,
)


class GetIngestionControl(ABC):
    @abstractmethod
    async def execute(
        self,
        input_dto: GetIngestionControlInput,
    ) -> GetIngestionControlOutput: ...


class UpdateIngestionControl(ABC):
    @abstractmethod
    async def execute(
        self,
        input_dto: UpdateIngestionControlInput,
    ) -> UpdateIngestionControlOutput: ...
