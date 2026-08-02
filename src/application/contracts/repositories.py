from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from src.application.dtos.cursor_page import CursorPage
from src.application.dtos.ingestion_control import IngestionControlState
from src.application.dtos.ticket_ingestion import (
    BatchIngestionResult,
    TicketSourceRecord,
)
from src.domain.entities import (
    AuthSessionEntity,
    CustomerEntity,
    SatisfactionRatingEntity,
    TagEntity,
    TicketEntity,
    TicketTagEntity,
    UserEntity,
)

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    @abstractmethod
    async def add(self, entity: T) -> None: ...

    @abstractmethod
    async def get(self, entity_id: UUID) -> T | None: ...

    @abstractmethod
    async def update(self, entity: T) -> None: ...

    @abstractmethod
    async def delete(self, entity_id: UUID) -> None: ...

    @abstractmethod
    async def page(
        self,
        cursor: str | None,
        page_size: int = 20,
    ) -> CursorPage[T]: ...


class UserRepository(Repository[UserEntity]):
    @abstractmethod
    async def get_by_email(self, email: str) -> UserEntity | None: ...


class AuthSessionRepository(ABC):
    @abstractmethod
    async def add(self, entity: AuthSessionEntity) -> None: ...

    @abstractmethod
    async def get_for_update(
        self,
        session_id: UUID,
    ) -> AuthSessionEntity | None: ...

    @abstractmethod
    async def update(self, entity: AuthSessionEntity) -> None: ...

    @abstractmethod
    async def revoke_all_by_user(self, user_id: UUID) -> int: ...


class CustomerRepository(Repository[CustomerEntity]): ...


class TicketRepository(Repository[TicketEntity]):
    @abstractmethod
    async def page_by_tag_ids(
        self,
        tag_ids: list[UUID],
        cursor: str | None = None,
        page_size: int = 20,
    ) -> CursorPage[TicketEntity]: ...

    @abstractmethod
    async def synchronize_batch(
        self,
        records: list[TicketSourceRecord],
        *,
        invalid: int = 0,
        received: int | None = None,
    ) -> BatchIngestionResult: ...

    @abstractmethod
    async def get_ingestion_control(
        self,
        *,
        for_update: bool = False,
    ) -> IngestionControlState: ...

    @abstractmethod
    async def set_ingestion_enabled(
        self,
        enabled: bool,
    ) -> IngestionControlState: ...

    @abstractmethod
    async def mark_ingestion_processing(self) -> None: ...

    @abstractmethod
    async def complete_ingestion_cycle(
        self,
        *,
        next_cursor: int,
        source_version: str,
    ) -> None: ...

    @abstractmethod
    async def register_ingestion_error(self, message: str) -> None: ...


class SatisfactionRatingRepository(Repository[SatisfactionRatingEntity]): ...


class TagRepository(Repository[TagEntity]): ...


class TicketTagRepository(Repository[TicketTagEntity]):
    @abstractmethod
    async def delete_by_ticket_and_tag(
        self,
        ticket_id: UUID,
        tag_id: UUID,
    ) -> None: ...
