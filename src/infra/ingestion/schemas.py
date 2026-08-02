from pydantic import BaseModel

from src.application.dtos.ticket_ingestion import (
    BatchIngestionResult,
    SatisfactionSourceRecord,
    TicketSourceRecord,
)


class SourceBatch(BaseModel):
    version: str
    records: list[TicketSourceRecord]
    consumed: int
    invalid: int
    exhausted: bool


__all__ = [
    "BatchIngestionResult",
    "SatisfactionSourceRecord",
    "SourceBatch",
    "TicketSourceRecord",
]
