from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from src.application.dtos.analytics import (
    AnalyticsFilters,
    AssigneeFilterOption,
    CustomerAnalyticsQueryPage,
    CustomerFilterOption,
    CustomerMetricsInput,
    DashboardOperationalSnapshot,
    DashboardPeriodSnapshot,
    ExportTicketRecord,
    TagFilterOption,
)
from src.application.dtos.cursor_page import CursorPage
from src.application.dtos.ingestion_control import IngestionControlState
from src.application.dtos.ticket_ingestion import (
    CustomerSourceResult,
    SatisfactionSourceRecord,
    TicketSourceRecord,
    TicketSourceResult,
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


class CustomerRepository(Repository[CustomerEntity]):
    @abstractmethod
    async def upsert_from_source(
        self,
        *,
        external_requester_id: int,
        requester_name: str,
        requester_email: str,
    ) -> CustomerSourceResult: ...

    @abstractmethod
    async def list_filter_options(self) -> list[CustomerFilterOption]: ...


class TicketRepository(Repository[TicketEntity]):
    @abstractmethod
    async def page_by_tag_ids(
        self,
        tag_ids: list[UUID],
        cursor: str | None = None,
        page_size: int = 20,
    ) -> CursorPage[TicketEntity]: ...

    @abstractmethod
    async def upsert_from_source(
        self,
        record: TicketSourceRecord,
        *,
        customer_id: UUID,
    ) -> TicketSourceResult: ...

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
    async def complete_ingestion_cycle(self, *, next_cursor: int) -> None: ...

    @abstractmethod
    async def register_ingestion_error(self, message: str) -> None: ...

    @abstractmethod
    async def get_dashboard_period_snapshot(
        self,
        filters: AnalyticsFilters,
        top_topics_limit: int,
    ) -> DashboardPeriodSnapshot: ...

    @abstractmethod
    async def get_dashboard_operational_snapshot(
        self,
        filters: AnalyticsFilters,
        timeline_limit: int,
    ) -> DashboardOperationalSnapshot: ...

    @abstractmethod
    async def page_customer_analytics(
        self,
        input_dto: CustomerMetricsInput,
    ) -> CustomerAnalyticsQueryPage: ...

    @abstractmethod
    async def list_assignee_options(self) -> list[AssigneeFilterOption]: ...

    @abstractmethod
    async def count_export_rows(self, filters: AnalyticsFilters) -> int: ...

    @abstractmethod
    async def fetch_export_records(
        self,
        filters: AnalyticsFilters,
        limit: int,
        offset: int,
    ) -> list[ExportTicketRecord]: ...


class SatisfactionRatingRepository(Repository[SatisfactionRatingEntity]):
    @abstractmethod
    async def synchronize_from_source(
        self,
        *,
        ticket_id: UUID,
        source: SatisfactionSourceRecord | None,
    ) -> None: ...


class TagRepository(Repository[TagEntity]):
    @abstractmethod
    async def resolve_by_names(self, names: list[str]) -> dict[str, TagEntity]: ...

    @abstractmethod
    async def list_filter_options(self) -> list[TagFilterOption]: ...


class TicketTagRepository(Repository[TicketTagEntity]):
    @abstractmethod
    async def delete_by_ticket_and_tag(
        self,
        ticket_id: UUID,
        tag_id: UUID,
    ) -> None: ...

    @abstractmethod
    async def replace_for_ticket(
        self,
        *,
        ticket_id: UUID,
        tag_ids: list[UUID],
    ) -> None: ...
