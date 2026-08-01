from typing import Any

from fastapi import APIRouter, Body
from fastapi import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse

from src.bootstrap.composers.ingestion_control import (
    get_ingestion_control_composer,
    update_ingestion_control_composer,
)
from src.presentation.http.fastapi.adapters import adapt_request, adapt_response


router = APIRouter(prefix="/ingestion/control", tags=["ingestion"])


@router.get("")
async def get_ingestion_control(request: FastAPIRequest) -> FastAPIResponse:
    response = await get_ingestion_control_composer()(adapt_request(request))
    return adapt_response(response)


@router.patch("")
async def update_ingestion_control(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await update_ingestion_control_composer()(adapt_request(request, body))
    return adapt_response(response)
