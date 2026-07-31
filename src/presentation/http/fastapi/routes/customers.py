from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body
from fastapi import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse

from src.bootstrap.composers.customers import (
    add_customer_composer,
    delete_customer_composer,
    get_customer_composer,
    list_customers_composer,
    update_customer_composer,
)
from src.presentation.http.fastapi.adapters import adapt_request, adapt_response


router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("")
async def add_customer(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await add_customer_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.get("")
async def list_customers(request: FastAPIRequest) -> FastAPIResponse:
    response = await list_customers_composer()(adapt_request(request))
    return adapt_response(response)


@router.get("/{customer_id}")
async def get_customer(
    customer_id: UUID,
    request: FastAPIRequest,
) -> FastAPIResponse:
    response = await get_customer_composer()(adapt_request(request))
    return adapt_response(response)


@router.patch("/{customer_id}")
async def update_customer(
    customer_id: UUID,
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await update_customer_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: UUID,
    request: FastAPIRequest,
) -> FastAPIResponse:
    response = await delete_customer_composer()(adapt_request(request))
    return adapt_response(response)
