from __future__ import annotations

from src.application.dtos.analytics import CustomerMetricsInput, DashboardInput
from src.application.use_cases.analytics import GetDashboardOverview, ListCustomerMetrics
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class GetDashboardOverviewController(Controller):
    def __init__(self, use_case: GetDashboardOverview) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        output = await self._use_case.execute(DashboardInput(**request.query))
        return Response(status_code=200, body=output)


class ListCustomerMetricsController(Controller):
    def __init__(self, use_case: ListCustomerMetrics) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        output = await self._use_case.execute(CustomerMetricsInput(**request.query))
        return Response(status_code=200, body=output.model_dump(mode="json"))
