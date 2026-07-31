from datetime import datetime, timedelta, timezone
from uuid import uuid7

from src.application.contracts.repositories import (
    AuthSessionRepository,
    UserRepository,
)
from src.application.contracts.security import (
    AccessTokenService,
    PasswordHasher,
    RefreshTokenService,
)
from src.application.dtos.auth import (
    AuthenticateUserInput,
    AuthTokensOutput,
    LogoutAllAuthSessionsInput,
    LogoutAllAuthSessionsOutput,
    LogoutAuthSessionInput,
    LogoutAuthSessionOutput,
    RefreshAuthSessionInput,
    RefreshAuthSessionResult,
    UserView,
)
from src.domain.entities import AuthSessionEntity


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuthenticateUser:
    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: AuthSessionRepository,
        password_hasher: PasswordHasher,
        access_token_service: AccessTokenService,
        refresh_token_service: RefreshTokenService,
        access_token_expires_in: int,
        refresh_token_expires_in: int,
    ) -> None:
        self._user_repository = user_repository
        self._session_repository = session_repository
        self._password_hasher = password_hasher
        self._access_token_service = access_token_service
        self._refresh_token_service = refresh_token_service
        self._access_token_expires_in = access_token_expires_in
        self._refresh_token_expires_in = refresh_token_expires_in

    async def execute(
        self,
        input_dto: AuthenticateUserInput,
    ) -> AuthTokensOutput | None:
        user = await self._user_repository.get_by_email(input_dto.email)
        if user is None:
            return None

        password_matches = await self._password_hasher.verify(
            input_dto.password,
            user.password_hash,
        )
        if not password_matches or user.id is None:
            return None

        now = _utc_now()
        session_id = uuid7()
        refresh_token = self._refresh_token_service.create(session_id)
        session = AuthSessionEntity(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=self._refresh_token_service.hash(refresh_token),
            expires_at=now + timedelta(seconds=self._refresh_token_expires_in),
            last_used_at=now,
            user_agent=input_dto.user_agent,
            ip_address=input_dto.ip_address,
        )
        await self._session_repository.add(session)

        return AuthTokensOutput(
            user=UserView.model_validate(user),
            session_id=session_id,
            access_token=self._access_token_service.create(user.id, session_id),
            refresh_token=refresh_token,
            access_token_expires_in=self._access_token_expires_in,
            refresh_token_expires_in=self._refresh_token_expires_in,
        )


class RefreshAuthSession:
    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: AuthSessionRepository,
        access_token_service: AccessTokenService,
        refresh_token_service: RefreshTokenService,
        access_token_expires_in: int,
        refresh_token_expires_in: int,
    ) -> None:
        self._user_repository = user_repository
        self._session_repository = session_repository
        self._access_token_service = access_token_service
        self._refresh_token_service = refresh_token_service
        self._access_token_expires_in = access_token_expires_in
        self._refresh_token_expires_in = refresh_token_expires_in

    async def execute(
        self,
        input_dto: RefreshAuthSessionInput,
    ) -> RefreshAuthSessionResult:
        try:
            session_id = self._refresh_token_service.get_session_id(
                input_dto.refresh_token,
            )
        except ValueError:
            return RefreshAuthSessionResult(error_code="invalid_refresh_token")

        session = await self._session_repository.get_for_update(session_id)
        now = _utc_now()
        if (
            session is None
            or session.revoked_at is not None
            or session.expires_at <= now
        ):
            return RefreshAuthSessionResult(error_code="invalid_refresh_token")

        if not self._refresh_token_service.verify(
            input_dto.refresh_token,
            session.refresh_token_hash,
        ):
            session.revoked_at = now
            session.compromised_at = now
            await self._session_repository.update(session)
            return RefreshAuthSessionResult(error_code="refresh_token_reused")

        user = await self._user_repository.get(session.user_id)
        if user is None or user.id is None:
            session.revoked_at = now
            await self._session_repository.update(session)
            return RefreshAuthSessionResult(error_code="invalid_refresh_token")

        new_refresh_token = self._refresh_token_service.create(session_id)
        session.refresh_token_hash = self._refresh_token_service.hash(
            new_refresh_token,
        )
        session.last_used_at = now
        session.rotation_counter += 1
        await self._session_repository.update(session)

        tokens = AuthTokensOutput(
            user=UserView.model_validate(user),
            session_id=session_id,
            access_token=self._access_token_service.create(user.id, session_id),
            refresh_token=new_refresh_token,
            access_token_expires_in=self._access_token_expires_in,
            refresh_token_expires_in=self._refresh_token_expires_in,
        )
        return RefreshAuthSessionResult(tokens=tokens)


class LogoutAuthSession:
    def __init__(
        self,
        session_repository: AuthSessionRepository,
        refresh_token_service: RefreshTokenService,
    ) -> None:
        self._session_repository = session_repository
        self._refresh_token_service = refresh_token_service

    async def execute(
        self,
        input_dto: LogoutAuthSessionInput,
    ) -> LogoutAuthSessionOutput:
        if not input_dto.refresh_token:
            return LogoutAuthSessionOutput(revoked=False)

        try:
            session_id = self._refresh_token_service.get_session_id(
                input_dto.refresh_token,
            )
        except ValueError:
            return LogoutAuthSessionOutput(revoked=False)

        session = await self._session_repository.get_for_update(session_id)
        if session is None:
            return LogoutAuthSessionOutput(revoked=False)

        now = _utc_now()
        if not self._refresh_token_service.verify(
            input_dto.refresh_token,
            session.refresh_token_hash,
        ):
            session.compromised_at = now
        session.revoked_at = session.revoked_at or now
        await self._session_repository.update(session)
        return LogoutAuthSessionOutput(revoked=True)


class LogoutAllAuthSessions:
    def __init__(self, session_repository: AuthSessionRepository) -> None:
        self._session_repository = session_repository

    async def execute(
        self,
        input_dto: LogoutAllAuthSessionsInput,
    ) -> LogoutAllAuthSessionsOutput:
        revoked = await self._session_repository.revoke_all_by_user(
            input_dto.user_id,
        )
        return LogoutAllAuthSessionsOutput(revoked_sessions=revoked)
