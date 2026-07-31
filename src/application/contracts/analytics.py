from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from src.application.dtos.analytics import AnalyticsFilters, CustomerMetricsInput
from src.domain.analytics import RawField, ReportFormat


class AnalyticsQueryRepository(ABC):
    @abstractmethod
    async def get_dashboard(
        self,
        filters: AnalyticsFilters,
        top_topics_limit: int,
        timeline_limit: int,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def list_customer_metrics(
        self,
        input_dto: CustomerMetricsInput,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def count_raw_rows(self, filters: AnalyticsFilters) -> int: ...

    @abstractmethod
    async def fetch_raw_rows(
        self,
        filters: AnalyticsFilters,
        fields: list[RawField],
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]: ...


class ReportWriter(ABC):
    @abstractmethod
    def write(
        self,
        rows: Iterable[dict[str, Any]],
        columns: list[str],
        sheet_name: str,
    ) -> bytes: ...


class ReportWriterFactory(ABC):
    @abstractmethod
    def create(self, report_format: ReportFormat) -> ReportWriter: ...
