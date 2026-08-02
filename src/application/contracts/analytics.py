from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.application.dtos.analytics import AnalyticsFilters, CustomerMetricsInput


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
