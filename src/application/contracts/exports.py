from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.application.dtos.analytics import AnalyticsFilters
from src.domain.analytics import DataExportField


class DataExportRepository(ABC):
    @abstractmethod
    async def count_rows(self, filters: AnalyticsFilters) -> int: ...

    @abstractmethod
    async def fetch_rows(
        self,
        filters: AnalyticsFilters,
        fields: list[DataExportField],
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_filter_options(self) -> dict[str, list[dict[str, Any]]]: ...
