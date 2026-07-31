from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Query
from fastapi import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse

from src.bootstrap.composers.ticket_tags import list_tickets_by_tags_composer
from src.bootstrap.composers.tickets import (
    add_ticket_composer,
    delete_ticket_composer,
    get_ticket_composer,
    list_tickets_composer,
    update_ticket_composer,
)
from src.presentation.http.fastapi.adapters import adapt_request, adapt_response


router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("")
async def add_ticket(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await add_ticket_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.get("")
async def list_tickets(request: FastAPIRequest) -> FastAPIResponse:
    response = await list_tickets_composer()(adapt_request(request))
    return adapt_response(response)


@router.get("/by-tags")
async def list_tickets_by_tags(
    request: FastAPIRequest,
    tag_ids: Annotated[list[UUID], Query(min_length=1)],
) -> FastAPIResponse:
    internal_request = adapt_request(request)
    internal_request.query_params["tag_ids"] = tag_ids
    response = await list_tickets_by_tags_composer()(internal_request)
    return adapt_response(response)


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: UUID,
    request: FastAPIRequest,
) -> FastAPIResponse:
    response = await get_ticket_composer()(adapt_request(request))
    return adapt_response(response)


@router.patch("/{ticket_id}")
async def update_ticket(
    ticket_id: UUID,
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await update_ticket_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.delete("/{ticket_id}")
async def delete_ticket(
    ticket_id: UUID,
    request: FastAPIRequest,
) -> FastAPIResponse:
    response = await delete_ticket_composer()(adapt_request(request))
    return adapt_response(response)
