from __future__ import annotations

from typing import Any

from src.application.contracts.analytics import AnalyticsQueryRepository
from src.application.dtos.analytics import (
    CustomerMetricsInput,
    CustomerMetricsPage,
    DashboardInput,
)


class GetDashboardOverview:
    def __init__(self, repository: AnalyticsQueryRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: DashboardInput) -> dict[str, Any]:
        return await self._repository.get_dashboard(
            input_dto,
            input_dto.top_topics_limit,
            input_dto.timeline_limit,
        )


class ListCustomerMetrics:
    def __init__(self, repository: AnalyticsQueryRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: CustomerMetricsInput) -> CustomerMetricsPage:
        result = await self._repository.list_customer_metrics(input_dto)
        return CustomerMetricsPage(**result)
