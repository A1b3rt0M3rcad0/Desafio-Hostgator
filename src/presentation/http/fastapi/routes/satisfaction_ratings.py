from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body
from fastapi import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse

from src.bootstrap.composers.satisfaction_ratings import (
    add_satisfaction_rating_composer,
    delete_satisfaction_rating_composer,
    get_satisfaction_rating_composer,
    list_satisfaction_ratings_composer,
    update_satisfaction_rating_composer,
)
from src.presentation.http.fastapi.adapters import adapt_request, adapt_response


router = APIRouter(
    prefix="/satisfaction-ratings",
    tags=["satisfaction-ratings"],
)


@router.post("")
async def add_satisfaction_rating(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await add_satisfaction_rating_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.get("")
async def list_satisfaction_ratings(
    request: FastAPIRequest,
) -> FastAPIResponse:
    response = await list_satisfaction_ratings_composer()(adapt_request(request))
    return adapt_response(response)


@router.get("/{satisfaction_rating_id}")
async def get_satisfaction_rating(
    satisfaction_rating_id: UUID,
    request: FastAPIRequest,
) -> FastAPIResponse:
    response = await get_satisfaction_rating_composer()(adapt_request(request))
    return adapt_response(response)


@router.patch("/{satisfaction_rating_id}")
async def update_satisfaction_rating(
    satisfaction_rating_id: UUID,
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await update_satisfaction_rating_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.delete("/{satisfaction_rating_id}")
async def delete_satisfaction_rating(
    satisfaction_rating_id: UUID,
    request: FastAPIRequest,
) -> FastAPIResponse:
    response = await delete_satisfaction_rating_composer()(adapt_request(request))
    return adapt_response(response)
