from fastapi import APIRouter
from fastapi import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse

from src.bootstrap.composers.analytics import (
    get_dashboard_overview_composer,
    list_customer_metrics_composer,
)
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
