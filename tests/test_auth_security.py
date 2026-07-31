from uuid import uuid4

from src.infra.security import (
    JwtAccessTokenService,
    OpaqueRefreshTokenService,
    SignedCsrfTokenService,
)


def test_access_token_round_trip() -> None:
    service = JwtAccessTokenService(
        secret_key="x" * 64,
        algorithm="HS256",
        issuer="issuer",
        audience="audience",
        expires_in_seconds=60,
    )
    user_id = uuid4()
    session_id = uuid4()
    claims = service.decode(service.create(user_id, session_id))
    assert claims.user_id == user_id
    assert claims.session_id == session_id


def test_refresh_token_is_bound_to_session_and_hashed() -> None:
    service = OpaqueRefreshTokenService("p" * 64)
    session_id = uuid4()
    token = service.create(session_id)
    digest = service.hash(token)
    assert service.get_session_id(token) == session_id
    assert service.verify(token, digest)
    assert not service.verify(token + "x", digest)


def test_csrf_token_is_signed_and_bound() -> None:
    service = SignedCsrfTokenService("c" * 64)
    token = service.create("session-a")
    assert service.verify(token, "session-a")
    assert not service.verify(token, "session-b")
