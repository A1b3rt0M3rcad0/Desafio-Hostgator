import os
from dataclasses import dataclass
from typing import Literal, cast

from dotenv import load_dotenv

from src.infra.security import (
    BcryptPasswordHasher,
    JwtAccessTokenService,
    OpaqueRefreshTokenService,
    SignedCsrfTokenService,
)


def _required_secret(name: str) -> str:
    value = os.getenv(name)
    if (
        value is None
        or len(value) < 32
        or value.startswith("replace_with")
    ):
        raise RuntimeError(f"{name} must contain a generated secret of at least 32 characters.")
    return value


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_origins(value: str | None) -> tuple[str, ...]:
    if not value:
        return ("http://localhost:5173",)
    return tuple(origin.strip().rstrip("/") for origin in value.split(",") if origin.strip())


@dataclass(frozen=True)
class AuthSettings:
    access_token_expires_in: int
    refresh_token_expires_in: int
    access_cookie_name: str
    refresh_cookie_name: str
    csrf_cookie_name: str
    csrf_header_name: str
    cookie_secure: bool
    cookie_samesite: Literal["lax", "strict", "none"]
    cookie_domain: str | None
    allowed_origins: tuple[str, ...]
    trusted_origins: frozenset[str]


load_dotenv()

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
if JWT_ALGORITHM != "HS256":
    raise RuntimeError("JWT_ALGORITHM must be HS256 for this implementation.")

ACCESS_TOKEN_EXPIRES_IN = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"),
) * 60
REFRESH_TOKEN_EXPIRES_IN = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"),
) * 24 * 60 * 60
cookie_samesite_value = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()
if cookie_samesite_value not in {"lax", "strict", "none"}:
    raise RuntimeError("AUTH_COOKIE_SAMESITE must be lax, strict or none.")
COOKIE_SAMESITE = cast(
    Literal["lax", "strict", "none"],
    cookie_samesite_value,
)

_allowed_origins = _as_origins(os.getenv("CORS_ALLOWED_ORIGINS"))
_trusted_origins = _as_origins(
    os.getenv("TRUSTED_ORIGINS") or os.getenv("CORS_ALLOWED_ORIGINS"),
)

COOKIE_SECURE = _as_bool(os.getenv("AUTH_COOKIE_SECURE"), False)
COOKIE_DOMAIN = os.getenv("AUTH_COOKIE_DOMAIN") or None
if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
    raise RuntimeError("SameSite=None requires AUTH_COOKIE_SECURE=true.")

AUTH_SETTINGS = AuthSettings(
    access_token_expires_in=ACCESS_TOKEN_EXPIRES_IN,
    refresh_token_expires_in=REFRESH_TOKEN_EXPIRES_IN,
    access_cookie_name=os.getenv("AUTH_ACCESS_COOKIE_NAME", "access_token"),
    refresh_cookie_name=os.getenv("AUTH_REFRESH_COOKIE_NAME", "refresh_token"),
    csrf_cookie_name=os.getenv("AUTH_CSRF_COOKIE_NAME", "csrf_token"),
    csrf_header_name=os.getenv("CSRF_HEADER_NAME", "X-CSRF-Token"),
    cookie_secure=COOKIE_SECURE,
    cookie_samesite=COOKIE_SAMESITE,
    cookie_domain=COOKIE_DOMAIN,
    allowed_origins=_allowed_origins,
    trusted_origins=frozenset(_trusted_origins),
)

PASSWORD_HASHER = BcryptPasswordHasher(
    rounds=int(os.getenv("BCRYPT_ROUNDS", "12")),
)
ACCESS_TOKEN_SERVICE = JwtAccessTokenService(
    secret_key=_required_secret("JWT_SECRET_KEY"),
    algorithm=JWT_ALGORITHM,
    issuer=os.getenv("JWT_ISSUER", "desafio-hostgator-api"),
    audience=os.getenv("JWT_AUDIENCE", "desafio-hostgator-web"),
    expires_in_seconds=ACCESS_TOKEN_EXPIRES_IN,
)
REFRESH_TOKEN_SERVICE = OpaqueRefreshTokenService(
    pepper=_required_secret("REFRESH_TOKEN_PEPPER"),
)
CSRF_TOKEN_SERVICE = SignedCsrfTokenService(
    secret_key=_required_secret("CSRF_SECRET_KEY"),
)

for cookie_name in (
    AUTH_SETTINGS.access_cookie_name,
    AUTH_SETTINGS.refresh_cookie_name,
    AUTH_SETTINGS.csrf_cookie_name,
):
    if cookie_name.startswith("__Host-") and (
        not AUTH_SETTINGS.cookie_secure
        or AUTH_SETTINGS.cookie_domain is not None
    ):
        raise RuntimeError(
            "__Host- cookies require Secure=true and no Domain attribute.",
        )
