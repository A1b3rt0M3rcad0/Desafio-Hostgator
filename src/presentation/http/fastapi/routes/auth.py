from typing import Any

from fastapi import APIRouter, Body, Depends
from fastapi import Request as FastAPIRequest
from starlette.responses import Response as FastAPIResponse

from src.bootstrap.composers.auth import (
    authenticate_user_composer,
    current_user_composer,
    issue_csrf_token_controller,
    logout_all_auth_sessions_composer,
    logout_auth_session_composer,
    refresh_auth_session_composer,
)
from src.bootstrap.composers.users import add_user_composer
from src.presentation.http.fastapi.adapters import adapt_request, adapt_response
from src.presentation.http.fastapi.security import (
    require_anonymous_csrf,
    require_authenticated_request,
    require_logout_csrf,
    require_refresh_csrf,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/csrf")
async def issue_csrf(request: FastAPIRequest) -> FastAPIResponse:
    response = await issue_csrf_token_controller().handle(adapt_request(request))
    return adapt_response(response)


@router.post("/register", dependencies=[Depends(require_anonymous_csrf)])
async def register(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await add_user_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.post("/login", dependencies=[Depends(require_anonymous_csrf)])
async def login(
    request: FastAPIRequest,
    body: dict[str, Any] = Body(...),
) -> FastAPIResponse:
    response = await authenticate_user_composer()(adapt_request(request, body))
    return adapt_response(response)


@router.post("/refresh", dependencies=[Depends(require_refresh_csrf)])
async def refresh(request: FastAPIRequest) -> FastAPIResponse:
    response = await refresh_auth_session_composer()(adapt_request(request))
    return adapt_response(response)


@router.post("/logout", dependencies=[Depends(require_logout_csrf)])
async def logout(request: FastAPIRequest) -> FastAPIResponse:
    response = await logout_auth_session_composer()(adapt_request(request))
    return adapt_response(response)


@router.post("/logout-all", dependencies=[Depends(require_authenticated_request)])
async def logout_all(request: FastAPIRequest) -> FastAPIResponse:
    response = await logout_all_auth_sessions_composer()(adapt_request(request))
    return adapt_response(response)


@router.get("/me", dependencies=[Depends(require_authenticated_request)])
async def me(request: FastAPIRequest) -> FastAPIResponse:
    response = await current_user_composer()(adapt_request(request))
    return adapt_response(response)
