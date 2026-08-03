from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterable
from typing import Any, TypeAlias

from src.domain.analytics import ReportFormat

ReportRow: TypeAlias = dict[str, Any]
ReportRowBatch: TypeAlias = list[ReportRow]
ReportRowBatches: TypeAlias = AsyncIterator[ReportRowBatch]


class ReportWriter(ABC):
    @abstractmethod
    def write(
        self,
        rows: Iterable[ReportRow],
        columns: list[str],
        sheet_name: str,
    ) -> bytes: ...


class StreamingReportWriter(ABC):
    @abstractmethod
    async def write(
        self,
        row_batches: ReportRowBatches,
        columns: list[str],
        sheet_name: str,
    ) -> AsyncIterator[bytes]: ...


class ReportWriterFactory(ABC):
    @abstractmethod
    def create(self, report_format: ReportFormat) -> ReportWriter: ...

    @abstractmethod
    def create_streaming(
        self,
        report_format: ReportFormat,
    ) -> StreamingReportWriter: ...
