from __future__ import annotations

from urllib.parse import quote

from src.application.dtos.analytics import (
    CustomerMetricsInput,
    DashboardInput,
    MetricExportInput,
    RawExportInput,
    RawPreviewInput,
)
from src.application.use_cases.analytics import (
    ExportMetricsReport,
    ExportRawReport,
    GetDashboardOverview,
    GetReportCatalog,
    ListCustomerMetrics,
    PreviewRawReport,
)
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


class GetReportCatalogController(Controller):
    def __init__(self, use_case: GetReportCatalog) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        del request
        return Response(status_code=200, body=await self._use_case.execute())


class PreviewRawReportController(Controller):
    def __init__(self, use_case: PreviewRawReport) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        output = await self._use_case.execute(RawPreviewInput(**(request.body or {})))
        return Response(status_code=200, body=output.model_dump(mode="json"))


class ExportRawReportController(Controller):
    def __init__(self, use_case: ExportRawReport) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        output = await self._use_case.execute(RawExportInput(**(request.body or {})))
        return self._download_response(output.filename, output.media_type, output.content)

    @staticmethod
    def _download_response(filename: str, media_type: str, content: bytes) -> Response:
        encoded = quote(filename)
        return Response(
            status_code=200,
            body=content,
            headers={
                "Content-Type": media_type,
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
                "Content-Length": str(len(content)),
                "Cache-Control": "no-store",
            },
        )


class ExportMetricsReportController(Controller):
    def __init__(self, use_case: ExportMetricsReport) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        output = await self._use_case.execute(MetricExportInput(**(request.body or {})))
        return ExportRawReportController._download_response(
            output.filename,
            output.media_type,
            output.content,
        )
