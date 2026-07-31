from typing import Any

from fastapi import Request as FastAPIRequest
from starlette.datastructures import QueryParams

from src.presentation.http.schemas.request import Request


def _adapt_query_params(query_params: QueryParams) -> dict[str, Any]:
    adapted: dict[str, Any] = {}

    for key in query_params.keys():
        values = query_params.getlist(key)
        adapted[key] = values if len(values) > 1 else values[0]

    return adapted


def adapt_request(
    request: FastAPIRequest,
    body: Any = None,
) -> Request:
    return Request(
        user=getattr(request.state, "user", None),
        url=str(request.url),
        method=request.method,
        headers=dict(request.headers),
        cookies=dict(request.cookies),
        client_ip=request.client.host if request.client else None,
        body=body,
        query_params=_adapt_query_params(request.query_params),
        path_params=dict(request.path_params),
    )
