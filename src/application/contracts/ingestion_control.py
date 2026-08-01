from abc import ABC, abstractmethod

from src.application.dtos.ingestion_control import (
    GetIngestionControlInput,
    GetIngestionControlOutput,
    IngestionControlState,
    UpdateIngestionControlInput,
    UpdateIngestionControlOutput,
)


class IngestionControlRepository(ABC):
    @abstractmethod
    async def get(self) -> IngestionControlState: ...

    @abstractmethod
    async def set_enabled(self, enabled: bool) -> IngestionControlState: ...


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
