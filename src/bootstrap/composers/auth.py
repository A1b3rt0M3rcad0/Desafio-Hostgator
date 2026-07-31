from src.application.use_cases.auth import (
    AuthenticateUser,
    LogoutAllAuthSessions,
    LogoutAuthSession,
    RefreshAuthSession,
)
from src.bootstrap.composers.database import DATABASE_ENGINE
from src.bootstrap.security import (
    ACCESS_TOKEN_SERVICE,
    AUTH_SETTINGS,
    CSRF_TOKEN_SERVICE,
    PASSWORD_HASHER,
    REFRESH_TOKEN_SERVICE,
)
from src.infra.database.repositories import (
    SqlAlchemyAuthSessionRepository,
    SqlAlchemyUserRepository,
)
from src.infra.database.transactional_handler import TransactionalHandler
from src.infra.database.unit_of_work import UnitOfWork
from src.presentation.http.controllers.auth_controller import (
    AuthenticateUserController,
    CurrentUserController,
    IssueCsrfTokenController,
    LogoutAllAuthSessionsController,
    LogoutAuthSessionController,
    RefreshAuthSessionController,
    create_cookie_factory,
)


def _repositories():
    unit_of_work = UnitOfWork(DATABASE_ENGINE)
    return (
        unit_of_work,
        SqlAlchemyUserRepository(unit_of_work),
        SqlAlchemyAuthSessionRepository(unit_of_work),
    )


def _cookies():
    return create_cookie_factory(AUTH_SETTINGS, CSRF_TOKEN_SERVICE)


def authenticate_user_composer() -> TransactionalHandler:
    unit_of_work, users, sessions = _repositories()
    use_case = AuthenticateUser(
        users,
        sessions,
        PASSWORD_HASHER,
        ACCESS_TOKEN_SERVICE,
        REFRESH_TOKEN_SERVICE,
        AUTH_SETTINGS.access_token_expires_in,
        AUTH_SETTINGS.refresh_token_expires_in,
    )
    return TransactionalHandler(
        unit_of_work,
        AuthenticateUserController(use_case, _cookies()).handle,
    )


def refresh_auth_session_composer() -> TransactionalHandler:
    unit_of_work, users, sessions = _repositories()
    use_case = RefreshAuthSession(
        users,
        sessions,
        ACCESS_TOKEN_SERVICE,
        REFRESH_TOKEN_SERVICE,
        AUTH_SETTINGS.access_token_expires_in,
        AUTH_SETTINGS.refresh_token_expires_in,
    )
    return TransactionalHandler(
        unit_of_work,
        RefreshAuthSessionController(
            use_case,
            _cookies(),
            AUTH_SETTINGS,
        ).handle,
    )


def logout_auth_session_composer() -> TransactionalHandler:
    unit_of_work, _, sessions = _repositories()
    use_case = LogoutAuthSession(sessions, REFRESH_TOKEN_SERVICE)
    return TransactionalHandler(
        unit_of_work,
        LogoutAuthSessionController(
            use_case,
            _cookies(),
            AUTH_SETTINGS,
        ).handle,
    )


def logout_all_auth_sessions_composer() -> TransactionalHandler:
    unit_of_work, _, sessions = _repositories()
    use_case = LogoutAllAuthSessions(sessions)
    return TransactionalHandler(
        unit_of_work,
        LogoutAllAuthSessionsController(use_case, _cookies()).handle,
    )


def issue_csrf_token_controller() -> IssueCsrfTokenController:
    return IssueCsrfTokenController(_cookies())


def current_user_controller() -> CurrentUserController:
    return CurrentUserController()
