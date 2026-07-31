import asyncio
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid7

import bcrypt
import jwt

from src.application.contracts.security import (
    AccessTokenService,
    PasswordHasher,
    RefreshTokenService,
)
from src.application.dtos.auth import AccessTokenClaims


class BcryptPasswordHasher(PasswordHasher):
    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    async def hash(self, password: str) -> bytes:
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=self._rounds)
        return await asyncio.to_thread(bcrypt.hashpw, password_bytes, salt)

    async def verify(self, password: str, password_hash: bytes) -> bool:
        try:
            return await asyncio.to_thread(
                bcrypt.checkpw,
                password.encode("utf-8"),
                password_hash,
            )
        except ValueError:
            return False


class JwtAccessTokenService(AccessTokenService):
    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        issuer: str,
        audience: str,
        expires_in_seconds: int,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._issuer = issuer
        self._audience = audience
        self._expires_in_seconds = expires_in_seconds

    def create(self, user_id: UUID, session_id: UUID) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "sid": str(session_id),
            "jti": str(uuid7()),
            "type": "access",
            "iss": self._issuer,
            "aud": self._audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(seconds=self._expires_in_seconds),
        }
        return jwt.encode(
            payload,
            self._secret_key,
            algorithm=self._algorithm,
        )

    def decode(self, token: str) -> AccessTokenClaims:
        payload = jwt.decode(
            token,
            self._secret_key,
            algorithms=[self._algorithm],
            audience=self._audience,
            issuer=self._issuer,
            options={
                "require": [
                    "sub",
                    "sid",
                    "jti",
                    "type",
                    "iss",
                    "aud",
                    "iat",
                    "nbf",
                    "exp",
                ],
            },
        )
        if payload["type"] != "access":
            raise jwt.InvalidTokenError("Invalid token type.")
        return AccessTokenClaims(
            user_id=UUID(payload["sub"]),
            session_id=UUID(payload["sid"]),
            token_id=UUID(payload["jti"]),
        )


class OpaqueRefreshTokenService(RefreshTokenService):
    def __init__(self, pepper: str) -> None:
        self._pepper = pepper.encode("utf-8")

    def create(self, session_id: UUID) -> str:
        return f"{session_id}.{secrets.token_urlsafe(48)}"

    def get_session_id(self, token: str) -> UUID:
        session_id, separator, secret = token.partition(".")
        if not separator or not secret:
            raise ValueError("Malformed refresh token.")
        return UUID(session_id)

    def hash(self, token: str) -> bytes:
        return hmac.new(
            self._pepper,
            token.encode("utf-8"),
            hashlib.sha256,
        ).digest()

    def verify(self, token: str, expected_hash: bytes) -> bool:
        return hmac.compare_digest(self.hash(token), expected_hash)


class SignedCsrfTokenService:
    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key.encode("utf-8")

    def create(self, binding: str) -> str:
        nonce = secrets.token_urlsafe(32)
        signature = self._sign(binding, nonce)
        return f"{nonce}.{signature}"

    def verify(self, token: str, binding: str) -> bool:
        nonce, separator, signature = token.partition(".")
        if not separator or not nonce or not signature:
            return False
        expected = self._sign(binding, nonce)
        return hmac.compare_digest(signature, expected)

    def _sign(self, binding: str, nonce: str) -> str:
        message = f"{binding}.{nonce}".encode("utf-8")
        return hmac.new(
            self._secret_key,
            message,
            hashlib.sha256,
        ).hexdigest()
