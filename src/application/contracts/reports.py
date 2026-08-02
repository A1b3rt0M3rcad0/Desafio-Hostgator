from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, TypeAlias

from src.domain.analytics import ReportFormat

ReportRow: TypeAlias = dict[str, Any]


class ReportWriter(ABC):
    @abstractmethod
    def write(
        self,
        rows: Iterable[ReportRow],
        columns: list[str],
        sheet_name: str,
    ) -> bytes: ...


class ReportWriterFactory(ABC):
    @abstractmethod
    def create(self, report_format: ReportFormat) -> ReportWriter: ...
