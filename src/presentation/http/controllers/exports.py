from __future__ import annotations

from urllib.parse import quote

from src.application.dtos.exports import (
    DataExportInput,
    DataExportPreviewInput,
    ExportedFile,
    MetricsExportInput,
)
from src.application.use_cases.exports import (
    ExportData,
    ExportMetrics,
    GetExportCatalog,
    PreviewDataExport,
)
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response


class GetExportCatalogController(Controller):
    def __init__(self, use_case: GetExportCatalog) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        del request
        return Response(status_code=200, body=await self._use_case.execute())


class PreviewDataExportController(Controller):
    def __init__(self, use_case: PreviewDataExport) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        output = await self._use_case.execute(
            DataExportPreviewInput(**(request.body or {}))
        )
        return Response(status_code=200, body=output.model_dump(mode="json"))


class ExportDataController(Controller):
    def __init__(self, use_case: ExportData) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        output = await self._use_case.execute(
            DataExportInput(**(request.body or {}))
        )
        return self._download_response(output)

    @staticmethod
    def _download_response(output: ExportedFile) -> Response:
        encoded = quote(output.filename)
        headers = {
            "Content-Type": output.media_type,
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
            "Cache-Control": "no-store",
        }
        if output.content is not None:
            headers["Content-Length"] = str(len(output.content))
        return Response(
            status_code=200,
            body=output.content,
            stream=output.stream,
            headers=headers,
        )


class ExportMetricsController(Controller):
    def __init__(self, use_case: ExportMetrics) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        output = await self._use_case.execute(
            MetricsExportInput(**(request.body or {}))
        )
        return ExportDataController._download_response(output)
