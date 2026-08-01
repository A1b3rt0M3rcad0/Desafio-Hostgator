from typing import Any

from fastapi import APIRouter, Body
from fastapi import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse

from src.bootstrap.composers.analytics import (
    export_metrics_report_composer,
    export_raw_report_composer,
    get_dashboard_overview_composer,
    get_report_catalog_composer,
    list_customer_metrics_composer,
    preview_raw_report_composer,
)
from src.bootstrap.composers.imports import sync_tickets_from_mock_composer
from src.presentation.http.fastapi.adapters import adapt_request, adapt_response


router = APIRouter(tags=["analytics"])


@router.get("/dashboard")
async def dashboard(request: FastAPIRequest) -> FastAPIResponse:
    response = await get_dashboard_overview_composer()(adapt_request(request))
    return adapt_response(response)


@router.get("/metrics/customers")
async def customer_metrics(request: FastAPIRequest) -> FastAPIResponse:
    response = await list_customer_metrics_composer()(adapt_request(request))
    return adapt_response(response)


@router.get("/reports/catalog")
async def report_catalog(request: FastAPIRequest) -> FastAPIResponse:
    response = await get_report_catalog_composer()(adapt_request(request))
    return adapt_response(response)


@router.post("/reports/raw/preview")
async def preview_raw_report(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await preview_raw_report_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.post("/reports/raw/export")
async def export_raw_report(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await export_raw_report_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.post("/reports/metrics/export")
async def export_metrics_report(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await export_metrics_report_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.post("/imports/tickets/sync")
async def sync_tickets_from_mock(
    request: FastAPIRequest,
    body: Any = Body(...),
) -> FastAPIResponse:
    response = await sync_tickets_from_mock_composer()(adapt_request(request, body))
    return adapt_response(response)
