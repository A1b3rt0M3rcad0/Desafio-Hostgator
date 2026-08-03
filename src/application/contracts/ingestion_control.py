
from abc import ABC, abstractmethod

from src.application.dtos.ingestion_control import (
    GetIngestionControlOutput,
    UpdateIngestionControlInput,
    UpdateIngestionControlOutput,
)
from src.application.dtos.ticket_ingestion import (
    IngestTicketBatchInput,
    IngestTicketBatchOutput,
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


class IngestTicketBatch(ABC):
    @abstractmethod
    async def execute(
        self,
        input_dto: IngestTicketBatchInput,
    ) -> IngestTicketBatchOutput: ...
