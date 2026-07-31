from src.application.dtos.auth import (
    AuthenticateUserInput,
    LogoutAllAuthSessionsInput,
    LogoutAuthSessionInput,
    RefreshAuthSessionInput,
)
from src.application.use_cases.auth import (
    AuthenticateUser,
    LogoutAllAuthSessions,
    LogoutAuthSession,
    RefreshAuthSession,
)
from src.bootstrap.security import AuthSettings
from src.infra.security import SignedCsrfTokenService
from src.presentation.http.controllers.controller import Controller
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response, ResponseCookie


class _AuthCookieFactory:
    def __init__(
        self,
        settings: AuthSettings,
        csrf_service: SignedCsrfTokenService,
    ) -> None:
        self._settings = settings
        self._csrf_service = csrf_service

    def authenticated(self, access_token: str, refresh_token: str, session_id) -> list[ResponseCookie]:
        csrf_token = self._csrf_service.create(str(session_id))
        return [
            self._cookie(
                self._settings.access_cookie_name,
                access_token,
                self._settings.access_token_expires_in,
                httponly=True,
            ),
            self._cookie(
                self._settings.refresh_cookie_name,
                refresh_token,
                self._settings.refresh_token_expires_in,
                httponly=True,
            ),
            self._cookie(
                self._settings.csrf_cookie_name,
                csrf_token,
                self._settings.refresh_token_expires_in,
                httponly=False,
            ),
        ]

    def anonymous_csrf(self) -> ResponseCookie:
        return self._cookie(
            self._settings.csrf_cookie_name,
            self._csrf_service.create("anonymous"),
            self._settings.refresh_token_expires_in,
            httponly=False,
        )

    def delete_all(self) -> list[ResponseCookie]:
        return [
            self._delete(self._settings.access_cookie_name, httponly=True),
            self._delete(self._settings.refresh_cookie_name, httponly=True),
            self._delete(self._settings.csrf_cookie_name, httponly=False),
        ]

    def _cookie(self, key: str, value: str, max_age: int, httponly: bool) -> ResponseCookie:
        return ResponseCookie(
            key=key,
            value=value,
            max_age=max_age,
            domain=self._settings.cookie_domain,
            secure=self._settings.cookie_secure,
            httponly=httponly,
            samesite=self._settings.cookie_samesite,
        )

    def _delete(self, key: str, httponly: bool) -> ResponseCookie:
        return ResponseCookie(
            key=key,
            delete=True,
            domain=self._settings.cookie_domain,
            secure=self._settings.cookie_secure,
            httponly=httponly,
            samesite=self._settings.cookie_samesite,
        )


class IssueCsrfTokenController(Controller):
    def __init__(self, cookies: _AuthCookieFactory) -> None:
        self._cookies = cookies

    async def handle(self, request: Request) -> Response:
        return Response(
            status_code=204,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
            cookies=[self._cookies.anonymous_csrf()],
        )


class AuthenticateUserController(Controller):
    def __init__(self, use_case: AuthenticateUser, cookies: _AuthCookieFactory) -> None:
        self._use_case = use_case
        self._cookies = cookies

    async def handle(self, request: Request) -> Response:
        input_dto = AuthenticateUserInput(
            email=request.body.get("email"),
            password=request.body.get("password"),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client_ip,
        )
        output = await self._use_case.execute(input_dto)
        if output is None:
            return Response(
                status_code=401,
                headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
                body={
                    "error": {
                        "code": "invalid_credentials",
                        "message": "Invalid email or password.",
                    },
                },
            )
        return Response(
            status_code=200,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
            body={
                "user": output.user.model_dump(),
                "access_token_expires_in": output.access_token_expires_in,
            },
            cookies=self._cookies.authenticated(
                output.access_token,
                output.refresh_token,
                output.session_id,
            ),
        )


class RefreshAuthSessionController(Controller):
    def __init__(
        self,
        use_case: RefreshAuthSession,
        cookies: _AuthCookieFactory,
        settings: AuthSettings,
    ) -> None:
        self._use_case = use_case
        self._cookies = cookies
        self._settings = settings

    async def handle(self, request: Request) -> Response:
        refresh_token = request.cookies.get(
            self._settings.refresh_cookie_name,
            "",
        )
        result = await self._use_case.execute(
            RefreshAuthSessionInput(refresh_token=refresh_token),
        )
        if result.tokens is None:
            return Response(
                status_code=401,
                headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
                body={
                    "error": {
                        "code": result.error_code or "invalid_refresh_token",
                        "message": "The authentication session is no longer valid.",
                    },
                },
                cookies=self._cookies.delete_all(),
            )
        output = result.tokens
        return Response(
            status_code=200,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
            body={
                "user": output.user.model_dump(),
                "access_token_expires_in": output.access_token_expires_in,
            },
            cookies=self._cookies.authenticated(
                output.access_token,
                output.refresh_token,
                output.session_id,
            ),
        )


class LogoutAuthSessionController(Controller):
    def __init__(self, use_case: LogoutAuthSession, cookies: _AuthCookieFactory, settings: AuthSettings) -> None:
        self._use_case = use_case
        self._cookies = cookies
        self._settings = settings

    async def handle(self, request: Request) -> Response:
        await self._use_case.execute(
            LogoutAuthSessionInput(
                refresh_token=request.cookies.get(self._settings.refresh_cookie_name),
            ),
        )
        return Response(
            status_code=204,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
            cookies=self._cookies.delete_all(),
        )


class LogoutAllAuthSessionsController(Controller):
    def __init__(self, use_case: LogoutAllAuthSessions, cookies: _AuthCookieFactory) -> None:
        self._use_case = use_case
        self._cookies = cookies

    async def handle(self, request: Request) -> Response:
        if request.user is None:
            return Response(status_code=401)
        await self._use_case.execute(
            LogoutAllAuthSessionsInput(user_id=request.user.id),
        )
        return Response(
            status_code=204,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
            cookies=self._cookies.delete_all(),
        )


class CurrentUserController(Controller):
    async def handle(self, request: Request) -> Response:
        if request.user is None:
            return Response(status_code=401)
        return Response(
            status_code=200,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
            body={
                "id": request.user.id,
                "session_id": request.user.session_id,
            },
        )


def create_cookie_factory(settings: AuthSettings, csrf_service: SignedCsrfTokenService) -> _AuthCookieFactory:
    return _AuthCookieFactory(settings, csrf_service)
