import hmac
from urllib.parse import urlsplit

import jwt
from fastapi import HTTPException, Request, status

from src.application.dtos.auth import AuthenticatedUser
from src.bootstrap.security import (
    ACCESS_TOKEN_SERVICE,
    AUTH_SETTINGS,
    CSRF_TOKEN_SERVICE,
    REFRESH_TOKEN_SERVICE,
)

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _origin_from_referer(referer: str) -> str:
    parsed = urlsplit(referer)
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _validate_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        referer = request.headers.get("referer")
        origin = _origin_from_referer(referer) if referer else None
    if origin is None or origin.rstrip("/") not in AUTH_SETTINGS.trusted_origins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Untrusted request origin.",
        )
    if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-site request rejected.",
        )


def _validate_csrf(request: Request, binding: str) -> None:
    if request.method not in UNSAFE_METHODS:
        return
    _validate_origin(request)
    cookie_token = request.cookies.get(AUTH_SETTINGS.csrf_cookie_name)
    header_token = request.headers.get(AUTH_SETTINGS.csrf_header_name)
    if (
        not cookie_token
        or not header_token
        or not hmac.compare_digest(cookie_token, header_token)
        or not CSRF_TOKEN_SERVICE.verify(cookie_token, binding)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token.",
        )


async def require_anonymous_csrf(request: Request) -> None:
    _validate_csrf(request, "anonymous")


async def require_refresh_csrf(request: Request) -> None:
    refresh_token = request.cookies.get(AUTH_SETTINGS.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required.",
        )
    try:
        session_id = REFRESH_TOKEN_SERVICE.get_session_id(refresh_token)
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        ) from exception
    _validate_csrf(request, str(session_id))


async def require_logout_csrf(request: Request) -> None:
    refresh_token = request.cookies.get(AUTH_SETTINGS.refresh_cookie_name)
    if not refresh_token:
        _validate_csrf(request, "anonymous")
        return
    try:
        session_id = REFRESH_TOKEN_SERVICE.get_session_id(refresh_token)
    except ValueError:
        access_token = request.cookies.get(AUTH_SETTINGS.access_cookie_name)
        if access_token:
            try:
                claims = ACCESS_TOKEN_SERVICE.decode(access_token)
                _validate_csrf(request, str(claims.session_id))
                return
            except (jwt.InvalidTokenError, ValueError):
                pass
        _validate_csrf(request, "anonymous")
        return
    _validate_csrf(request, str(session_id))


async def require_authenticated_request(request: Request) -> AuthenticatedUser:
    access_token = request.cookies.get(AUTH_SETTINGS.access_cookie_name)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    try:
        claims = ACCESS_TOKEN_SERVICE.decode(access_token)
    except jwt.ExpiredSignatureError as exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token expired.",
        ) from exception
    except (jwt.InvalidTokenError, ValueError) as exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
        ) from exception

    authenticated_user = AuthenticatedUser(
        id=claims.user_id,
        session_id=claims.session_id,
    )
    request.state.user = authenticated_user
    request.state.session_id = claims.session_id
    _validate_csrf(request, str(claims.session_id))
    return authenticated_user
