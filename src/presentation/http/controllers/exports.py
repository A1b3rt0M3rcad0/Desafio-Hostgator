from __future__ import annotations

from urllib.parse import quote

from src.application.dtos.exports import (
    DataExportInput,
    DataExportPreviewInput,
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
        output = await self._use_case.execute(DataExportInput(**(request.body or {})))
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


class ExportMetricsController(Controller):
    def __init__(self, use_case: ExportMetrics) -> None:
        self._use_case = use_case

    async def handle(self, request: Request) -> Response:
        output = await self._use_case.execute(MetricsExportInput(**(request.body or {})))
        return ExportDataController._download_response(
            output.filename,
            output.media_type,
            output.content,
        )
