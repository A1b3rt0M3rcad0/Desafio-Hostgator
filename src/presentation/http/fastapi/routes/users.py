from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body
from fastapi import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse

from src.bootstrap.composers.users import (
    add_user_composer,
    delete_user_composer,
    get_user_composer,
    list_users_composer,
    update_user_composer,
)
from src.presentation.http.fastapi.adapters import adapt_request, adapt_response


router = APIRouter(prefix="/users", tags=["users"])


@router.post("")
async def add_user(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await add_user_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.get("")
async def list_users(request: FastAPIRequest) -> FastAPIResponse:
    response = await list_users_composer()(adapt_request(request))
    return adapt_response(response)


@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    request: FastAPIRequest,
) -> FastAPIResponse:
    response = await get_user_composer()(adapt_request(request))
    return adapt_response(response)


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await update_user_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    request: FastAPIRequest,
) -> FastAPIResponse:
    response = await delete_user_composer()(adapt_request(request))
    return adapt_response(response)
