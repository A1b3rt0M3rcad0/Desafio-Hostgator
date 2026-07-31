from typing import Any

from fastapi import APIRouter, Body
from fastapi import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse

from src.bootstrap.composers.ticket_tags import (
    add_ticket_tag_composer,
    delete_ticket_tag_composer,
)
from src.presentation.http.fastapi.adapters import adapt_request, adapt_response


router = APIRouter(prefix="/ticket-tags", tags=["ticket-tags"])


@router.post("")
async def add_ticket_tag(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await add_ticket_tag_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.delete("")
async def delete_ticket_tag(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await delete_ticket_tag_composer()(adapt_request(request, body))
    return adapt_response(response)
