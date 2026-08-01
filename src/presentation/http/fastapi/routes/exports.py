from typing import Any

from fastapi import APIRouter, Body
from fastapi import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse

from src.bootstrap.composers.exports import (
    export_data_composer,
    export_metrics_composer,
    get_export_catalog_composer,
    preview_data_export_composer,
)
from src.presentation.http.fastapi.adapters import adapt_request, adapt_response


router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/catalog")
async def export_catalog(request: FastAPIRequest) -> FastAPIResponse:
    response = await get_export_catalog_composer()(adapt_request(request))
    return adapt_response(response)


@router.post("/data/preview")
async def preview_data_export(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await preview_data_export_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.post("/data/download")
async def export_data(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await export_data_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.post("/metrics/download")
async def export_metrics(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await export_metrics_composer()(adapt_request(request, body))
    return adapt_response(response)
