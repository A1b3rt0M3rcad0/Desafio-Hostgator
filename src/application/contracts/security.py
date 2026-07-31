from abc import ABC, abstractmethod
from uuid import UUID

from src.application.dtos.auth import AccessTokenClaims


class PasswordHasher(ABC):
    @abstractmethod
    async def hash(self, password: str) -> bytes: ...

    @abstractmethod
    async def verify(self, password: str, password_hash: bytes) -> bool: ...


class AccessTokenService(ABC):
    @abstractmethod
    def create(self, user_id: UUID, session_id: UUID) -> str: ...

    @abstractmethod
    def decode(self, token: str) -> AccessTokenClaims: ...


class RefreshTokenService(ABC):
    @abstractmethod
    def create(self, session_id: UUID) -> str: ...

    @abstractmethod
    def get_session_id(self, token: str) -> UUID: ...

    @abstractmethod
    def hash(self, token: str) -> bytes: ...

    @abstractmethod
    def verify(self, token: str, expected_hash: bytes) -> bool: ...
