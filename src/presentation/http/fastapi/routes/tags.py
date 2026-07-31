from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body
from fastapi import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse

from src.bootstrap.composers.tags import (
    add_tag_composer,
    delete_tag_composer,
    get_tag_composer,
    list_tags_composer,
    update_tag_composer,
)
from src.presentation.http.fastapi.adapters import adapt_request, adapt_response


router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("")
async def add_tag(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await add_tag_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.get("")
async def list_tags(request: FastAPIRequest) -> FastAPIResponse:
    response = await list_tags_composer()(adapt_request(request))
    return adapt_response(response)


@router.get("/{tag_id}")
async def get_tag(
    tag_id: UUID,
    request: FastAPIRequest,
) -> FastAPIResponse:
    response = await get_tag_composer()(adapt_request(request))
    return adapt_response(response)


@router.patch("/{tag_id}")
async def update_tag(
    tag_id: UUID,
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await update_tag_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: UUID,
    request: FastAPIRequest,
) -> FastAPIResponse:
    response = await delete_tag_composer()(adapt_request(request))
    return adapt_response(response)
