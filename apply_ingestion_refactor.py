from __future__ import annotations

import json
import re
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    if content.count(old) != 1:
        raise RuntimeError(
            f"Expected exactly one occurrence in {path}; found {content.count(old)}: {old[:120]!r}"
        )
    write(path, content.replace(old, new, 1))


def regex_replace_once(path: str, pattern: str, replacement: str) -> None:
    content = read(path)
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"Pattern did not match exactly once in {path}: {pattern[:120]!r}")
    write(path, updated)


# Domain: the existing customer entity becomes the monitored-customer aggregate.
replace_once(
    "src/domain/entities.py",
    dedent(
        """
        class CustomerEntity(BaseEntity):
            external_requester_id: int
            requester_name: str
            requester_email: str
        """
    ).strip(),
    dedent(
        """
        class CustomerEntity(BaseEntity):
            external_requester_id: int | None = None
            requester_name: str
            requester_email: str
            is_monitored: bool = True
        """
    ).strip(),
)

# SQLAlchemy model: no new table/entity; only the monitored flag and optional external binding.
replace_once(
    "src/infra/database/models.py",
    dedent(
        """
        class Customer(BaseModel):
            __tablename__ = "customers"

            external_requester_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
            requester_name: Mapped[str] = mapped_column(String(255), nullable=False)
            requester_email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
            tickets: Mapped[list[Ticket]] = relationship(
        """
    ).strip(),
    dedent(
        """
        class Customer(BaseModel):
            __tablename__ = "customers"

            external_requester_id: Mapped[int | None] = mapped_column(
                BigInteger,
                unique=True,
                nullable=True,
            )
            requester_name: Mapped[str] = mapped_column(String(255), nullable=False)
            requester_email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
            is_monitored: Mapped[bool] = mapped_column(
                Boolean,
                nullable=False,
                default=True,
                server_default="1",
                index=True,
            )
            tickets: Mapped[list[Ticket]] = relationship(
        """
    ).strip(),
)

# Customer DTOs: the HelpDesk ID is auxiliary and can be bound by ingestion.
write(
    "src/application/dtos/add_customer.py",
    dedent(
        """
        from pydantic import BaseModel, Field, field_validator

        from src.domain.entities import CustomerEntity


        class AddCustomerInput(BaseModel):
            external_requester_id: int | None = Field(default=None, gt=0)
            requester_name: str
            requester_email: str

            @field_validator("requester_name")
            @classmethod
            def normalize_name(cls, value: str) -> str:
                normalized = value.strip()
                if not normalized:
                    raise ValueError("requester_name cannot be empty")
                return normalized

            @field_validator("requester_email")
            @classmethod
            def normalize_email(cls, value: str) -> str:
                normalized = value.strip().lower()
                if "@" not in normalized:
                    raise ValueError("requester_email must be valid")
                return normalized


        class AddCustomerOutput(BaseModel):
            customer: CustomerEntity
        """
    ),
)

write(
    "src/application/dtos/update_customer.py",
    dedent(
        """
        from uuid import UUID

        from pydantic import BaseModel, Field, field_validator

        from src.domain.entities import CustomerEntity


        class UpdateCustomerInput(BaseModel):
            customer_id: UUID
            external_requester_id: int | None = Field(default=None, gt=0)
            requester_name: str | None = None
            requester_email: str | None = None

            @field_validator("requester_name")
            @classmethod
            def normalize_name(cls, value: str | None) -> str | None:
                if value is None:
                    return None
                normalized = value.strip()
                if not normalized:
                    raise ValueError("requester_name cannot be empty")
                return normalized

            @field_validator("requester_email")
            @classmethod
            def normalize_email(cls, value: str | None) -> str | None:
                if value is None:
                    return None
                normalized = value.strip().lower()
                if "@" not in normalized:
                    raise ValueError("requester_email must be valid")
                return normalized


        class UpdateCustomerOutput(BaseModel):
            customer: CustomerEntity
        """
    ),
)

# Analytics/export DTOs must reflect that an unbound monitored customer has no external ID yet.
analytics = read("src/application/dtos/analytics.py")
analytics = analytics.replace("    external_requester_id: int\n", "    external_requester_id: int | None = None\n")
analytics = analytics.replace("    requester_id: int\n", "    requester_id: int | None = None\n")
write("src/application/dtos/analytics.py", analytics)

# Batch ingestion DTOs remain in the existing ticket_ingestion module.
write(
    "src/application/dtos/ticket_ingestion.py",
    dedent(
        """
        from __future__ import annotations

        from datetime import datetime
        from typing import Any

        from pydantic import BaseModel, Field, field_validator

        from src.domain.entities import SatisfactionScore, TicketPriority, TicketStatus


        class SatisfactionSourceRecord(BaseModel):
            score: SatisfactionScore
            offered_at: datetime | None = None
            rated_at: datetime | None = None
            comment: str = ""

            @field_validator("score", mode="before")
            @classmethod
            def normalize_score(cls, value: Any) -> Any:
                return str(value).upper() if value is not None else value

            @field_validator("comment", mode="before")
            @classmethod
            def normalize_comment(cls, value: Any) -> str:
                return "" if value is None else str(value)


        class TicketSourceRecord(BaseModel):
            ticket_id: int
            subject: str = Field(min_length=1, max_length=500)
            description: str = Field(min_length=1)
            status: TicketStatus
            priority: TicketPriority
            requester_id: int
            requester_name: str = Field(min_length=1, max_length=255)
            requester_email: str = Field(min_length=3, max_length=255)
            assignee_id: int | None = None
            assignee_name: str | None = Field(default=None, max_length=255)
            created_at: datetime
            updated_at: datetime
            first_response_at: datetime | None = None
            tags: list[str] = Field(default_factory=list)
            satisfaction_rating: SatisfactionSourceRecord | None = None

            @field_validator("status", "priority", mode="before")
            @classmethod
            def normalize_enum(cls, value: Any) -> Any:
                return str(value).upper() if value is not None else value

            @field_validator("requester_email")
            @classmethod
            def normalize_email(cls, value: str) -> str:
                return value.strip().lower()

            @field_validator("requester_name")
            @classmethod
            def normalize_name(cls, value: str) -> str:
                return value.strip()

            @field_validator("tags")
            @classmethod
            def normalize_tags(cls, value: list[str]) -> list[str]:
                return sorted({item.strip() for item in value if item and item.strip()})


        class IngestTicketBatchInput(BaseModel):
            expected_cursor: int = Field(ge=0)
            source_total: int = Field(gt=0)
            records: list[TicketSourceRecord]


        class IngestTicketBatchOutput(BaseModel):
            received: int
            matched_customers: int
            ignored_unmonitored: int
            identity_conflicts: int
            tickets_created: int
            tickets_updated: int
            tickets_unchanged: int
            next_cursor: int
        """
    ),
)

# Repository contracts: same file and repository families, now with explicit batch operations.
write(
    "src/application/contracts/repositories.py",
    dedent(
        """
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
        from src.application.dtos.ticket_ingestion import SatisfactionSourceRecord
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
            async def get_by_email(
                self,
                email: str,
                *,
                include_unmonitored: bool = False,
            ) -> CustomerEntity | None: ...

            @abstractmethod
            async def find_monitored_by_emails(
                self,
                emails: set[str],
            ) -> dict[str, CustomerEntity]: ...

            @abstractmethod
            async def update_many(self, customers: list[CustomerEntity]) -> None: ...

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
            async def get_by_external_ids(
                self,
                external_ticket_ids: set[int],
            ) -> dict[int, TicketEntity]: ...

            @abstractmethod
            async def insert_many(self, tickets: list[TicketEntity]) -> None: ...

            @abstractmethod
            async def update_many(self, tickets: list[TicketEntity]) -> None: ...

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

            @abstractmethod
            async def synchronize_many(
                self,
                ratings: dict[UUID, SatisfactionSourceRecord | None],
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

            @abstractmethod
            async def replace_many(
                self,
                tags_by_ticket: dict[UUID, list[UUID]],
            ) -> None: ...
        """
    ),
)

# Ingestion use-case contract stays in the existing ingestion_control contract module.
write(
    "src/application/contracts/ingestion_control.py",
    dedent(
        """
        from abc import ABC, abstractmethod

        from src.application.dtos.ingestion_control import (
            GetIngestionControlOutput,
            UpdateIngestionControlInput,
            UpdateIngestionControlOutput,
        )
        from src.application.dtos.ticket_ingestion import (
            IngestTicketBatchInput,
            IngestTicketBatchOutput,
        )


        class GetIngestionControl(ABC):
            @abstractmethod
            async def execute(self) -> GetIngestionControlOutput: ...


        class UpdateIngestionControl(ABC):
            @abstractmethod
            async def execute(
                self,
                input_dto: UpdateIngestionControlInput,
            ) -> UpdateIngestionControlOutput: ...


        class IngestTicketBatch(ABC):
            @abstractmethod
            async def execute(
                self,
                input_dto: IngestTicketBatchInput,
            ) -> IngestTicketBatchOutput: ...
        """
    ),
)

# Customer use cases: reactivation on create and soft deletion preserve history.
write(
    "src/application/use_cases/add_customer.py",
    dedent(
        """
        from src.application.contracts.repositories import CustomerRepository
        from src.application.contracts.use_cases import AddCustomer as AddCustomerContract
        from src.application.dtos.add_customer import AddCustomerInput, AddCustomerOutput
        from src.domain.entities import CustomerEntity


        class AddCustomer(AddCustomerContract):
            def __init__(self, repository: CustomerRepository) -> None:
                self._repository = repository

            async def execute(self, input_dto: AddCustomerInput) -> AddCustomerOutput:
                existing = await self._repository.get_by_email(
                    input_dto.requester_email,
                    include_unmonitored=True,
                )
                if existing is not None:
                    if existing.is_monitored:
                        raise ValueError(
                            f"Customer with email {input_dto.requester_email} already exists"
                        )
                    existing.is_monitored = True
                    existing.requester_name = input_dto.requester_name
                    if input_dto.external_requester_id is not None:
                        existing.external_requester_id = input_dto.external_requester_id
                    await self._repository.update(existing)
                    return AddCustomerOutput(customer=existing)

                entity = CustomerEntity(
                    external_requester_id=input_dto.external_requester_id,
                    requester_name=input_dto.requester_name,
                    requester_email=input_dto.requester_email,
                    is_monitored=True,
                )
                await self._repository.add(entity)
                return AddCustomerOutput(customer=entity)
        """
    ),
)

write(
    "src/application/use_cases/delete_customer.py",
    dedent(
        """
        from src.application.contracts.repositories import CustomerRepository
        from src.application.contracts.use_cases import DeleteCustomer as DeleteCustomerContract
        from src.application.dtos.delete_customer import DeleteCustomerInput, DeleteCustomerOutput


        class DeleteCustomer(DeleteCustomerContract):
            def __init__(self, repository: CustomerRepository) -> None:
                self._repository = repository

            async def execute(self, input_dto: DeleteCustomerInput) -> DeleteCustomerOutput:
                customer = await self._repository.get(input_dto.customer_id)
                if customer is None:
                    raise ValueError(f"Customer {input_dto.customer_id} not found")
                customer.is_monitored = False
                await self._repository.update(customer)
                return DeleteCustomerOutput(success=True)
        """
    ),
)

# The ingestion orchestration and decisions move into the existing application use-case module.
write(
    "src/application/use_cases/ingestion_control.py",
    dedent(
        """
        from __future__ import annotations

        from datetime import datetime, timezone
        from uuid import UUID

        from src.application.contracts.ingestion_control import (
            GetIngestionControl as GetIngestionControlContract,
            IngestTicketBatch as IngestTicketBatchContract,
            UpdateIngestionControl as UpdateIngestionControlContract,
        )
        from src.application.contracts.repositories import (
            CustomerRepository,
            SatisfactionRatingRepository,
            TagRepository,
            TicketRepository,
            TicketTagRepository,
        )
        from src.application.dtos.ingestion_control import (
            GetIngestionControlOutput,
            UpdateIngestionControlInput,
            UpdateIngestionControlOutput,
        )
        from src.application.dtos.ticket_ingestion import (
            IngestTicketBatchInput,
            IngestTicketBatchOutput,
            TicketSourceRecord,
        )
        from src.domain.entities import CustomerEntity, TicketEntity


        def _naive_utc(value: datetime | None) -> datetime | None:
            if value is None:
                return None
            if value.tzinfo is None:
                return value
            return value.astimezone(timezone.utc).replace(tzinfo=None)


        class GetIngestionControl(GetIngestionControlContract):
            def __init__(self, repository: TicketRepository) -> None:
                self._repository = repository

            async def execute(self) -> GetIngestionControlOutput:
                control = await self._repository.get_ingestion_control()
                return GetIngestionControlOutput(control=control)


        class UpdateIngestionControl(UpdateIngestionControlContract):
            def __init__(self, repository: TicketRepository) -> None:
                self._repository = repository

            async def execute(
                self,
                input_dto: UpdateIngestionControlInput,
            ) -> UpdateIngestionControlOutput:
                control = await self._repository.set_ingestion_enabled(input_dto.enabled)
                return UpdateIngestionControlOutput(control=control)


        class IngestTicketBatch(IngestTicketBatchContract):
            def __init__(
                self,
                customer_repository: CustomerRepository,
                ticket_repository: TicketRepository,
                tag_repository: TagRepository,
                ticket_tag_repository: TicketTagRepository,
                satisfaction_repository: SatisfactionRatingRepository,
            ) -> None:
                self._customers = customer_repository
                self._tickets = ticket_repository
                self._tags = tag_repository
                self._ticket_tags = ticket_tag_repository
                self._ratings = satisfaction_repository

            async def execute(
                self,
                input_dto: IngestTicketBatchInput,
            ) -> IngestTicketBatchOutput:
                control = await self._tickets.get_ingestion_control(for_update=True)
                if not control.enabled:
                    return IngestTicketBatchOutput(
                        received=0,
                        matched_customers=0,
                        ignored_unmonitored=0,
                        identity_conflicts=0,
                        tickets_created=0,
                        tickets_updated=0,
                        tickets_unchanged=0,
                        next_cursor=control.cursor_position,
                    )
                if control.cursor_position != input_dto.expected_cursor:
                    raise RuntimeError(
                        "Ingestion cursor changed while the batch was being prepared"
                    )

                records_by_ticket_id: dict[int, TicketSourceRecord] = {}
                for record in input_dto.records:
                    if record.ticket_id in records_by_ticket_id:
                        raise ValueError(
                            f"Duplicate ticket_id in source batch: {record.ticket_id}"
                        )
                    records_by_ticket_id[record.ticket_id] = record

                records = list(records_by_ticket_id.values())
                emails = {record.requester_email for record in records}
                customers_by_email = await self._customers.find_monitored_by_emails(
                    emails
                )

                customer_updates: dict[UUID, CustomerEntity] = {}
                matched_records: list[tuple[TicketSourceRecord, CustomerEntity]] = []
                matched_customer_ids: set[UUID] = set()
                ignored_unmonitored = 0
                identity_conflicts = 0

                for record in records:
                    customer = customers_by_email.get(record.requester_email)
                    if customer is None:
                        ignored_unmonitored += 1
                        continue
                    if customer.id is None:
                        raise RuntimeError("Persisted customer does not have an ID")
                    if customer.external_requester_id is None:
                        customer.external_requester_id = record.requester_id
                        customer_updates[customer.id] = customer
                    elif customer.external_requester_id != record.requester_id:
                        identity_conflicts += 1
                        continue
                    matched_records.append((record, customer))
                    matched_customer_ids.add(customer.id)

                if customer_updates:
                    await self._customers.update_many(list(customer_updates.values()))

                external_ticket_ids = {
                    record.ticket_id for record, _ in matched_records
                }
                existing_by_external_id = await self._tickets.get_by_external_ids(
                    external_ticket_ids
                )

                new_tickets: list[TicketEntity] = []
                updated_tickets: list[TicketEntity] = []
                changed: list[tuple[TicketSourceRecord, TicketEntity]] = []
                unchanged = 0

                for record, customer in matched_records:
                    assert customer.id is not None
                    existing = existing_by_external_id.get(record.ticket_id)
                    source_updated_at = _naive_utc(record.updated_at)
                    assert source_updated_at is not None
                    if existing is not None:
                        if existing.customer_id != customer.id:
                            identity_conflicts += 1
                            continue
                        if existing.source_updated_at >= source_updated_at:
                            unchanged += 1
                            continue
                        self._apply_source(existing, record, customer.id)
                        updated_tickets.append(existing)
                        changed.append((record, existing))
                        continue

                    ticket = TicketEntity(
                        customer_id=customer.id,
                        external_ticket_id=record.ticket_id,
                        subject=record.subject,
                        description=record.description,
                        first_response_at=_naive_utc(record.first_response_at),
                        status=record.status,
                        priority=record.priority,
                        assignee_external_id=record.assignee_id,
                        assignee_name=record.assignee_name,
                        source_created_at=_required_datetime(record.created_at),
                        source_updated_at=source_updated_at,
                    )
                    new_tickets.append(ticket)
                    changed.append((record, ticket))

                if new_tickets:
                    await self._tickets.insert_many(new_tickets)
                if updated_tickets:
                    await self._tickets.update_many(updated_tickets)

                all_tag_names = sorted(
                    {
                        tag_name
                        for record, _ in changed
                        for tag_name in record.tags
                    }
                )
                tags_by_name = await self._tags.resolve_by_names(all_tag_names)

                tags_by_ticket: dict[UUID, list[UUID]] = {}
                ratings_by_ticket = {}
                for record, ticket in changed:
                    if ticket.id is None:
                        raise RuntimeError("Ticket ID was not generated during batch insert")
                    tags_by_ticket[ticket.id] = [
                        tag.id
                        for name in record.tags
                        if (tag := tags_by_name.get(name)) is not None
                        and tag.id is not None
                    ]
                    ratings_by_ticket[ticket.id] = record.satisfaction_rating

                if tags_by_ticket:
                    await self._ticket_tags.replace_many(tags_by_ticket)
                    await self._ratings.synchronize_many(ratings_by_ticket)

                next_cursor = (
                    input_dto.expected_cursor + len(input_dto.records)
                ) % input_dto.source_total
                await self._tickets.complete_ingestion_cycle(next_cursor=next_cursor)

                return IngestTicketBatchOutput(
                    received=len(input_dto.records),
                    matched_customers=len(matched_customer_ids),
                    ignored_unmonitored=ignored_unmonitored,
                    identity_conflicts=identity_conflicts,
                    tickets_created=len(new_tickets),
                    tickets_updated=len(updated_tickets),
                    tickets_unchanged=unchanged,
                    next_cursor=next_cursor,
                )

            @staticmethod
            def _apply_source(
                ticket: TicketEntity,
                record: TicketSourceRecord,
                customer_id: UUID,
            ) -> None:
                ticket.customer_id = customer_id
                ticket.subject = record.subject
                ticket.description = record.description
                ticket.first_response_at = _naive_utc(record.first_response_at)
                ticket.status = record.status
                ticket.priority = record.priority
                ticket.assignee_external_id = record.assignee_id
                ticket.assignee_name = record.assignee_name
                ticket.source_created_at = _required_datetime(record.created_at)
                ticket.source_updated_at = _required_datetime(record.updated_at)


        def _required_datetime(value: datetime) -> datetime:
            normalized = _naive_utc(value)
            assert normalized is not None
            return normalized
        """
    ),
)

# Repository implementation: remove business-oriented upserts and add fixed-query batch operations.
repositories_path = "src/infra/database/repositories.py"
repositories = read(repositories_path)
repositories = repositories.replace(
    dedent(
        """
        from src.application.dtos.ticket_ingestion import (
            CustomerSourceResult,
            SatisfactionSourceRecord,
            TicketSourceRecord,
            TicketSourceResult,
        )
        """
    ).strip(),
    "from src.application.dtos.ticket_ingestion import SatisfactionSourceRecord",
)

repositories = repositories.replace(
    """    async def add(self, entity: CustomerEntity) -> None:\n        orm = Customer(**entity.model_dump(exclude={\"id\", \"created_at\", \"updated_at\"}))\n        self._session.add(orm)\n        await self._session.flush()\n""",
    """    async def add(self, entity: CustomerEntity) -> None:\n        orm = Customer(**entity.model_dump(exclude={\"id\", \"created_at\", \"updated_at\"}))\n        self._session.add(orm)\n        await self._session.flush()\n        entity.id = orm.id\n        entity.created_at = orm.created_at\n        entity.updated_at = orm.updated_at\n""",
    1,
)
repositories = repositories.replace(
    "stmt = select(Customer).order_by(Customer.id).limit(page_size + 1)",
    "stmt = (\n            select(Customer)\n            .where(Customer.is_monitored.is_(True))\n            .order_by(Customer.id)\n            .limit(page_size + 1)\n        )",
    1,
)
customer_methods = dedent(
    """
        async def get_by_email(
            self,
            email: str,
            *,
            include_unmonitored: bool = False,
        ) -> CustomerEntity | None:
            normalized = email.strip().lower()
            stmt = select(Customer).where(Customer.requester_email == normalized)
            if not include_unmonitored:
                stmt = stmt.where(Customer.is_monitored.is_(True))
            orm = (await self._session.execute(stmt)).scalar_one_or_none()
            return CustomerEntity.model_validate(orm) if orm else None

        async def find_monitored_by_emails(
            self,
            emails: set[str],
        ) -> dict[str, CustomerEntity]:
            normalized = {email.strip().lower() for email in emails if email.strip()}
            if not normalized:
                return {}
            rows = (
                await self._session.execute(
                    select(Customer).where(
                        Customer.requester_email.in_(normalized),
                        Customer.is_monitored.is_(True),
                    )
                )
            ).scalars().all()
            return {
                row.requester_email: CustomerEntity.model_validate(row)
                for row in rows
            }

        async def update_many(self, customers: list[CustomerEntity]) -> None:
            entities_by_id = {
                entity.id: entity for entity in customers if entity.id is not None
            }
            if not entities_by_id:
                return
            rows = (
                await self._session.execute(
                    select(Customer).where(Customer.id.in_(entities_by_id))
                )
            ).scalars().all()
            for row in rows:
                entity = entities_by_id[row.id]
                for key, value in entity.model_dump(
                    exclude={"id", "created_at", "updated_at"}
                ).items():
                    setattr(row, key, value)
            await self._session.flush()

        async def list_filter_options(self) -> list[CustomerFilterOption]:
    """
)
repositories, count = re.subn(
    r"\n    async def upsert_from_source\(\n        self,\n        \*,\n        external_requester_id: int,.*?\n    async def list_filter_options\(self\) -> list\[CustomerFilterOption\]:\n",
    "\n" + customer_methods,
    repositories,
    count=1,
    flags=re.DOTALL,
)
if count != 1:
    raise RuntimeError("Could not replace customer source upsert")
repositories = repositories.replace(
    ").order_by(Customer.requester_name.asc(), Customer.requester_email.asc())",
    ").where(Customer.is_monitored.is_(True)).order_by(\n                    Customer.requester_name.asc(),\n                    Customer.requester_email.asc(),\n                )",
    1,
)

repositories = repositories.replace(
    """    async def add(self, entity: TicketEntity) -> None:\n        orm = Ticket(**entity.model_dump(exclude={\"id\", \"created_at\", \"updated_at\"}))\n        self._session.add(orm)\n        await self._session.flush()\n""",
    """    async def add(self, entity: TicketEntity) -> None:\n        orm = Ticket(**entity.model_dump(exclude={\"id\", \"created_at\", \"updated_at\"}))\n        self._session.add(orm)\n        await self._session.flush()\n        entity.id = orm.id\n        entity.created_at = orm.created_at\n        entity.updated_at = orm.updated_at\n""",
    1,
)
ticket_batch_methods = dedent(
    """
        async def get_by_external_ids(
            self,
            external_ticket_ids: set[int],
        ) -> dict[int, TicketEntity]:
            if not external_ticket_ids:
                return {}
            rows = (
                await self._session.execute(
                    select(Ticket).where(
                        Ticket.external_ticket_id.in_(external_ticket_ids)
                    )
                )
            ).scalars().all()
            return {
                row.external_ticket_id: TicketEntity.model_validate(row)
                for row in rows
            }

        async def insert_many(self, tickets: list[TicketEntity]) -> None:
            if not tickets:
                return
            models = [
                Ticket(
                    **entity.model_dump(
                        exclude={"id", "created_at", "updated_at"}
                    )
                )
                for entity in tickets
            ]
            self._session.add_all(models)
            await self._session.flush()
            for entity, model in zip(tickets, models, strict=True):
                entity.id = model.id
                entity.created_at = model.created_at
                entity.updated_at = model.updated_at

        async def update_many(self, tickets: list[TicketEntity]) -> None:
            entities_by_id = {
                entity.id: entity for entity in tickets if entity.id is not None
            }
            if not entities_by_id:
                return
            rows = (
                await self._session.execute(
                    select(Ticket).where(Ticket.id.in_(entities_by_id))
                )
            ).scalars().all()
            for row in rows:
                entity = entities_by_id[row.id]
                for key, value in entity.model_dump(
                    exclude={"id", "created_at", "updated_at"}
                ).items():
                    setattr(row, key, value)
            await self._session.flush()

        async def get_ingestion_control(
    """
)
repositories, count = re.subn(
    r"\n    async def upsert_from_source\(\n        self,\n        record: TicketSourceRecord,.*?\n    async def get_ingestion_control\(\n",
    "\n" + ticket_batch_methods,
    repositories,
    count=1,
    flags=re.DOTALL,
)
if count != 1:
    raise RuntimeError("Could not replace ticket source upsert")

# Exclude soft-deleted customers from analytics/export queries while retaining their ticket history.
repositories = repositories.replace(
    """    def _ticket_predicates(self, filters: AnalyticsFilters) -> list[Any]:\n        predicates: list[Any] = []\n""",
    """    def _ticket_predicates(self, filters: AnalyticsFilters) -> list[Any]:\n        predicates: list[Any] = [\n            exists(\n                select(literal_column(\"1\"))\n                .select_from(Customer)\n                .where(\n                    Customer.id == Ticket.customer_id,\n                    Customer.is_monitored.is_(True),\n                )\n            )\n        ]\n""",
    1,
)

# Batch rating synchronization performs one read and one flush per batch.
rating_batch_method = dedent(
    """
        async def synchronize_many(
            self,
            ratings: dict[UUID, SatisfactionSourceRecord | None],
        ) -> None:
            if not ratings:
                return
            current_rows = (
                await self._session.execute(
                    select(SatisfactionRating).where(
                        SatisfactionRating.ticket_id.in_(ratings)
                    )
                )
            ).scalars().all()
            current_by_ticket = {row.ticket_id: row for row in current_rows}
            for ticket_id, source in ratings.items():
                current = current_by_ticket.get(ticket_id)
                if source is None:
                    if current is not None:
                        await self._session.delete(current)
                    continue
                values = {
                    "score": source.score,
                    "offered_at": _naive_utc(source.offered_at),
                    "rated_at": _naive_utc(source.rated_at),
                    "comment": source.comment,
                }
                if current is None:
                    self._session.add(
                        SatisfactionRating(ticket_id=ticket_id, **values)
                    )
                else:
                    for key, value in values.items():
                        setattr(current, key, value)
            await self._session.flush()


        class SqlAlchemyTagRepository
    """
)
repositories = repositories.replace(
    "\n\nclass SqlAlchemyTagRepository",
    "\n\n" + rating_batch_method.replace("\n\nclass SqlAlchemyTagRepository", "\n\nclass SqlAlchemyTagRepository"),
    1,
)
# The replacement above intentionally adds the class header token; normalize accidental indentation.
repositories = repositories.replace(
    "\n\nclass SqlAlchemyTagRepository\n(_SqlAlchemyRepository, TagRepository):",
    "\n\nclass SqlAlchemyTagRepository(_SqlAlchemyRepository, TagRepository):",
)
repositories = repositories.replace(
    "\n\nclass SqlAlchemyTagRepository\nclass SqlAlchemyTagRepository",
    "\n\nclass SqlAlchemyTagRepository",
)

# Add batch ticket-tag replacement at the end of the existing repository class.
replace_many_method = dedent(
    """

            async def replace_many(
                self,
                tags_by_ticket: dict[UUID, list[UUID]],
            ) -> None:
                ticket_ids = list(tags_by_ticket)
                if not ticket_ids:
                    return
                await self._session.execute(
                    delete(TicketTag).where(TicketTag.ticket_id.in_(ticket_ids))
                )
                links: list[TicketTag] = []
                seen: set[tuple[UUID, UUID]] = set()
                for ticket_id, tag_ids in tags_by_ticket.items():
                    for tag_id in tag_ids:
                        key = (ticket_id, tag_id)
                        if key in seen:
                            continue
                        seen.add(key)
                        links.append(TicketTag(ticket_id=ticket_id, tag_id=tag_id))
                self._session.add_all(links)
                await self._session.flush()
    """
)
repositories = repositories.rstrip() + replace_many_method + "\n"
write(repositories_path, repositories)

# Existing bootstrap folder composes the worker use case; the worker itself remains infrastructure-only.
write(
    "src/bootstrap/composers/ingestion_control.py",
    dedent(
        """
        from src.application.use_cases.ingestion_control import (
            GetIngestionControl,
            IngestTicketBatch,
            UpdateIngestionControl,
        )
        from src.bootstrap.composers.database import DATABASE_ENGINE
        from src.infra.database.repositories import (
            SqlAlchemyCustomerRepository,
            SqlAlchemySatisfactionRatingRepository,
            SqlAlchemyTagRepository,
            SqlAlchemyTicketRepository,
            SqlAlchemyTicketTagRepository,
        )
        from src.infra.database.transactional_handler import TransactionalHandler
        from src.infra.database.unit_of_work import UnitOfWork
        from src.presentation.http.controllers.ingestion_control import (
            GetIngestionControlController,
            UpdateIngestionControlController,
        )


        def get_ingestion_control_composer() -> TransactionalHandler:
            unit_of_work = UnitOfWork(DATABASE_ENGINE)
            repository = SqlAlchemyTicketRepository(unit_of_work)
            use_case = GetIngestionControl(repository)
            controller = GetIngestionControlController(use_case)
            return TransactionalHandler(unit_of_work, controller.handle)


        def update_ingestion_control_composer() -> TransactionalHandler:
            unit_of_work = UnitOfWork(DATABASE_ENGINE)
            repository = SqlAlchemyTicketRepository(unit_of_work)
            use_case = UpdateIngestionControl(repository)
            controller = UpdateIngestionControlController(use_case)
            return TransactionalHandler(unit_of_work, controller.handle)


        def ingest_ticket_batch_composer(
            unit_of_work: UnitOfWork,
        ) -> IngestTicketBatch:
            return IngestTicketBatch(
                customer_repository=SqlAlchemyCustomerRepository(unit_of_work),
                ticket_repository=SqlAlchemyTicketRepository(unit_of_work),
                tag_repository=SqlAlchemyTagRepository(unit_of_work),
                ticket_tag_repository=SqlAlchemyTicketTagRepository(unit_of_work),
                satisfaction_repository=SqlAlchemySatisfactionRatingRepository(
                    unit_of_work
                ),
            )
        """
    ),
)

# Worker: static source loading and scheduling only; all decisions live in the use case.
write(
    "src/infra/workers/ticket_ingestion_worker.py",
    dedent(
        """
        from __future__ import annotations

        import asyncio
        import json
        import logging
        import os
        import signal
        from dataclasses import dataclass
        from pathlib import Path

        from dotenv import load_dotenv
        from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

        from src.application.dtos.ticket_ingestion import (
            IngestTicketBatchInput,
            TicketSourceRecord,
        )
        from src.bootstrap.composers.ingestion_control import (
            ingest_ticket_batch_composer,
        )
        from src.infra.database.repositories import SqlAlchemyTicketRepository
        from src.infra.database.unit_of_work import UnitOfWork

        LOGGER = logging.getLogger(__name__)


        @dataclass(frozen=True, slots=True)
        class Settings:
            database_url: str
            source_path: Path
            batch_size: int
            interval_seconds: float
            poll_seconds: float

            @classmethod
            def from_env(cls) -> Settings:
                load_dotenv()
                database_url = os.getenv("MYSQL_URL_CONNECTION_WORKER")
                if not database_url:
                    raise RuntimeError("MYSQL_URL_CONNECTION_WORKER is required")
                return cls(
                    database_url=database_url,
                    source_path=Path(
                        os.getenv("WORKER_SOURCE_PATH", "/data/tickets.json")
                    ),
                    batch_size=int(os.getenv("WORKER_BATCH_SIZE", "30")),
                    interval_seconds=float(
                        os.getenv("WORKER_INTERVAL_SECONDS", "30")
                    ),
                    poll_seconds=float(
                        os.getenv("WORKER_CONTROL_POLL_SECONDS", "2")
                    ),
                )


        def read_ticket_source(path: Path) -> list[TicketSourceRecord]:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list) or not payload:
                raise ValueError("tickets.json must contain a non-empty list")
            records = [TicketSourceRecord.model_validate(item) for item in payload]
            ticket_ids = [record.ticket_id for record in records]
            if len(ticket_ids) != len(set(ticket_ids)):
                raise ValueError("tickets.json contains duplicate ticket_id values")
            return records


        async def run_cycle(
            engine: AsyncEngine,
            settings: Settings,
            source_records: list[TicketSourceRecord],
        ) -> bool | None:
            async with UnitOfWork(engine) as unit_of_work:
                repository = SqlAlchemyTicketRepository(unit_of_work)
                control = await repository.get_ingestion_control()

            if not control.enabled:
                return None

            source_total = len(source_records)
            start = control.cursor_position % source_total
            end = min(start + settings.batch_size, source_total)
            batch = source_records[start:end]

            async with UnitOfWork(engine) as unit_of_work:
                use_case = ingest_ticket_batch_composer(unit_of_work)
                result = await use_case.execute(
                    IngestTicketBatchInput(
                        expected_cursor=start,
                        source_total=source_total,
                        records=batch,
                    )
                )

            LOGGER.info(
                "ticket_ingestion.completed received=%s matched_customers=%s "
                "ignored_unmonitored=%s identity_conflicts=%s created=%s "
                "updated=%s unchanged=%s next_cursor=%s",
                result.received,
                result.matched_customers,
                result.ignored_unmonitored,
                result.identity_conflicts,
                result.tickets_created,
                result.tickets_updated,
                result.tickets_unchanged,
                result.next_cursor,
            )
            return True


        async def register_error(engine: AsyncEngine, error: Exception) -> None:
            async with UnitOfWork(engine) as unit_of_work:
                repository = SqlAlchemyTicketRepository(unit_of_work)
                await repository.register_ingestion_error(
                    str(error) or type(error).__name__
                )


        async def sleep_until_next_cycle(
            stop: asyncio.Event,
            seconds: float,
        ) -> None:
            try:
                await asyncio.wait_for(stop.wait(), timeout=seconds)
            except TimeoutError:
                pass


        async def run() -> None:
            settings = Settings.from_env()
            source_records = await asyncio.to_thread(
                read_ticket_source,
                settings.source_path,
            )
            engine = create_async_engine(settings.database_url, pool_pre_ping=True)
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for signal_name in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(signal_name, stop.set)
                except NotImplementedError:
                    pass

            LOGGER.info(
                "ticket_ingestion.started batch_size=%s interval_seconds=%s "
                "source_records=%s source_path=%s",
                settings.batch_size,
                settings.interval_seconds,
                len(source_records),
                settings.source_path,
            )
            try:
                while not stop.is_set():
                    try:
                        completed = await run_cycle(
                            engine,
                            settings,
                            source_records,
                        )
                        delay = (
                            settings.poll_seconds
                            if completed is None
                            else settings.interval_seconds
                        )
                    except Exception as error:
                        LOGGER.exception("ticket_ingestion.failed")
                        try:
                            await register_error(engine, error)
                        except Exception:
                            LOGGER.exception("ticket_ingestion.error_state_failed")
                        delay = settings.interval_seconds
                    await sleep_until_next_cycle(stop, delay)
            finally:
                await engine.dispose()


        def main() -> None:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s %(levelname)s %(name)s %(message)s",
            )
            asyncio.run(run())


        if __name__ == "__main__":
            main()
        """
    ),
)

# Frontend semantics: external ID is optional and deletion means stop monitoring.
frontend_path = "web/src/pages/DataPages.jsx"
frontend = read(frontend_path)
frontend = frontend.replace(
    "external_requester_id: String(customer.external_requester_id),",
    "external_requester_id: customer.external_requester_id ? String(customer.external_requester_id) : '',",
)
frontend = frontend.replace(
    """    const externalId = Number(form.external_requester_id);\n    if (!Number.isSafeInteger(externalId) || externalId <= 0) {\n      setMutationError(new Error('Informe um ID externo inteiro e positivo.'));\n      return;\n    }\n    const payload = {\n      external_requester_id: externalId,""",
    """    const externalIdText = form.external_requester_id.trim();\n    const externalId = externalIdText ? Number(externalIdText) : null;\n    if (externalId !== null && (!Number.isSafeInteger(externalId) || externalId <= 0)) {\n      setMutationError(new Error('O ID externo deve ser um inteiro positivo.'));\n      return;\n    }\n    const payload = {\n      external_requester_id: externalId,""",
)
frontend = frontend.replace(
    "const confirmed = window.confirm(`Excluir o cliente ${customer.requester_name}?`);",
    "const confirmed = window.confirm(`Remover ${customer.requester_name} do monitoramento? O histórico será preservado.`);",
)
frontend = frontend.replace(
    "description=\"Gerencie os clientes. A ingestão cria ou reutiliza registros pelo e-mail e pelo ID externo recebidos do HelpDesk.\"",
    "description=\"Cadastre os clientes monitorados. A ingestão cruza exclusivamente o e-mail cadastrado com a fonte HelpDesk.\"",
)
frontend = frontend.replace(
    '<label><span>ID externo</span><input type="number" min="1" required value={form.external_requester_id}',
    '<label><span>ID externo (opcional)</span><input type="number" min="1" value={form.external_requester_id}',
)
frontend = frontend.replace(
    "{ key: 'external_requester_id', label: 'ID externo' },",
    "{ key: 'external_requester_id', label: 'ID externo', render: (row) => row.external_requester_id || '—' },",
    1,
)
frontend = frontend.replace(
    ">Excluir</button>",
    ">Remover monitoramento</button>",
)
write(frontend_path, frontend)

# Docker now consumes a committed static source instead of generating a new snapshot each cycle.
compose = read("docker-compose.yaml")
for line in (
    '      MOCK_CUSTOMER_COUNT: "${MOCK_CUSTOMER_COUNT:-500}"\n',
    '      MOCK_START_TICKET_ID: "${MOCK_START_TICKET_ID:-100001}"\n',
    '      MOCK_YEAR: "${MOCK_YEAR:-2026}"\n',
    '      MOCK_SEED: "${MOCK_SEED:-hostgator-challenge-v4}"\n',
):
    compose = compose.replace(line, "")
write("docker-compose.yaml", compose)

# Commit the static source file; only temporary files remain ignored.
gitignore = read(".gitignore")
gitignore = gitignore.replace(
    "# Runtime snapshot overwritten by the worker every cycle\ndata/tickets.json\ndata/tickets.json.tmp",
    "# Temporary source generation files\ndata/tickets.json.tmp",
)
write(".gitignore", gitignore)

static_tickets = [
    {
        "ticket_id": 200001,
        "subject": "Sistema de login indisponível",
        "description": "O portal retorna erro 500 durante a autenticação.",
        "status": "open",
        "priority": "high",
        "requester_id": 44521,
        "requester_name": "Ana Beatriz Fernandes",
        "requester_email": "ana.fernandes@techcorp.com.br",
        "assignee_id": 9101,
        "assignee_name": "Patrícia Gomes (Suporte N1)",
        "created_at": "2026-05-02T10:05:00Z",
        "updated_at": "2026-05-02T10:25:00Z",
        "first_response_at": "2026-05-02T10:12:00Z",
        "tags": ["login", "portal", "erro-500"],
        "satisfaction_rating": {"score": "unoffered", "comment": ""},
    },
    {
        "ticket_id": 200002,
        "subject": "Erro ao redefinir senha",
        "description": "O link de redefinição expira antes do uso.",
        "status": "closed",
        "priority": "normal",
        "requester_id": 44521,
        "requester_name": "Ana Beatriz Fernandes",
        "requester_email": "ana.fernandes@techcorp.com.br",
        "assignee_id": 9101,
        "assignee_name": "Patrícia Gomes (Suporte N1)",
        "created_at": "2026-06-15T08:40:00Z",
        "updated_at": "2026-06-15T12:10:00Z",
        "first_response_at": "2026-06-15T08:52:00Z",
        "tags": ["login", "senha", "token-expirado"],
        "satisfaction_rating": {
            "score": "good",
            "offered_at": "2026-06-15T12:12:00Z",
            "rated_at": "2026-06-15T12:40:00Z",
            "comment": "Problema resolvido.",
        },
    },
    {
        "ticket_id": 200003,
        "subject": "Certificado SSL pendente",
        "description": "O certificado permanece aguardando validação do domínio.",
        "status": "hold",
        "priority": "high",
        "requester_id": 44521,
        "requester_name": "Ana Beatriz Fernandes",
        "requester_email": "ana.fernandes@techcorp.com.br",
        "assignee_id": 9108,
        "assignee_name": "Camila Rocha (Segurança e SSL)",
        "created_at": "2026-07-10T15:10:00Z",
        "updated_at": "2026-07-11T10:40:00Z",
        "first_response_at": "2026-07-10T15:28:00Z",
        "tags": ["ssl", "dominio", "validacao"],
        "satisfaction_rating": {"score": "unoffered", "comment": ""},
    },
    {
        "ticket_id": 200004,
        "subject": "Site apresentando erro 503",
        "description": "O site fica indisponível em horários de pico.",
        "status": "solved",
        "priority": "urgent",
        "requester_id": 44522,
        "requester_name": "Bruno Silva",
        "requester_email": "bruno.silva@lojaviva.com.br",
        "assignee_id": 9110,
        "assignee_name": "André Lima (Servidores e Performance)",
        "created_at": "2026-04-03T11:00:00Z",
        "updated_at": "2026-04-03T14:20:00Z",
        "first_response_at": "2026-04-03T11:08:00Z",
        "tags": ["erro-503", "performance", "hospedagem"],
        "satisfaction_rating": {
            "score": "good",
            "offered_at": "2026-04-03T14:22:00Z",
            "rated_at": "2026-04-03T15:00:00Z",
            "comment": "Atendimento rápido.",
        },
    },
    {
        "ticket_id": 200005,
        "subject": "Cobrança duplicada",
        "description": "Foram cobradas duas renovações para o mesmo período.",
        "status": "pending",
        "priority": "high",
        "requester_id": 44522,
        "requester_name": "Bruno Silva",
        "requester_email": "bruno.silva@lojaviva.com.br",
        "assignee_id": 9106,
        "assignee_name": "Juliana Martins (Financeiro)",
        "created_at": "2026-06-20T09:30:00Z",
        "updated_at": "2026-06-20T11:00:00Z",
        "first_response_at": "2026-06-20T09:45:00Z",
        "tags": ["cobranca", "duplicidade", "renovacao"],
        "satisfaction_rating": {"score": "offered", "offered_at": "2026-06-20T11:02:00Z", "comment": ""},
    },
    {
        "ticket_id": 200006,
        "subject": "Falha de autenticação SMTP",
        "description": "O cliente de e-mail não autentica no servidor de saída.",
        "status": "closed",
        "priority": "normal",
        "requester_id": 44522,
        "requester_name": "Bruno Silva",
        "requester_email": "bruno.silva@lojaviva.com.br",
        "assignee_id": 9104,
        "assignee_name": "Lucas Mendes (E-mail)",
        "created_at": "2026-07-02T13:00:00Z",
        "updated_at": "2026-07-02T15:30:00Z",
        "first_response_at": "2026-07-02T13:20:00Z",
        "tags": ["smtp", "email", "credenciais"],
        "satisfaction_rating": {
            "score": "bad",
            "offered_at": "2026-07-02T15:32:00Z",
            "rated_at": "2026-07-02T17:00:00Z",
            "comment": "Demorou mais que o esperado.",
        },
    },
    {
        "ticket_id": 200007,
        "subject": "Propagação de DNS",
        "description": "O domínio novo ainda não responde em todos os provedores.",
        "status": "open",
        "priority": "normal",
        "requester_id": 44523,
        "requester_name": "Camila Rocha",
        "requester_email": "camila.rocha@nexustech.com.br",
        "assignee_id": 9103,
        "assignee_name": "Marina Alves (Domínios e DNS)",
        "created_at": "2026-03-01T08:00:00Z",
        "updated_at": "2026-03-01T08:50:00Z",
        "first_response_at": "2026-03-01T08:10:00Z",
        "tags": ["dns", "propagacao", "dominio"],
        "satisfaction_rating": {"score": "unoffered", "comment": ""},
    },
    {
        "ticket_id": 200008,
        "subject": "Migração de site WordPress",
        "description": "Solicitação de migração integral do site e banco de dados.",
        "status": "solved",
        "priority": "high",
        "requester_id": 44523,
        "requester_name": "Camila Rocha",
        "requester_email": "camila.rocha@nexustech.com.br",
        "assignee_id": 9109,
        "assignee_name": "Diego Nunes (Migrações)",
        "created_at": "2026-05-18T10:00:00Z",
        "updated_at": "2026-05-19T16:00:00Z",
        "first_response_at": "2026-05-18T10:30:00Z",
        "tags": ["migracao", "wordpress", "backup"],
        "satisfaction_rating": {
            "score": "good",
            "offered_at": "2026-05-19T16:02:00Z",
            "rated_at": "2026-05-19T18:00:00Z",
            "comment": "Migração concluída.",
        },
    },
    {
        "ticket_id": 200009,
        "subject": "Uso elevado de CPU",
        "description": "A aplicação apresenta consumo elevado de recursos.",
        "status": "closed",
        "priority": "urgent",
        "requester_id": 44523,
        "requester_name": "Camila Rocha",
        "requester_email": "camila.rocha@nexustech.com.br",
        "assignee_id": 9110,
        "assignee_name": "André Lima (Servidores e Performance)",
        "created_at": "2026-07-25T07:30:00Z",
        "updated_at": "2026-07-25T12:00:00Z",
        "first_response_at": "2026-07-25T07:38:00Z",
        "tags": ["cpu", "memoria", "performance"],
        "satisfaction_rating": {
            "score": "good",
            "offered_at": "2026-07-25T12:02:00Z",
            "rated_at": "2026-07-25T12:20:00Z",
            "comment": "Resolvido no mesmo dia.",
        },
    },
]
write("data/tickets.json", json.dumps(static_tickets, ensure_ascii=False, indent=2))

# Schema migration: fields only, no new domain entity/table. Reset source offset after switching source semantics.
write(
    "migrations/versions/d2f4a6b8c010_monitored_customers.py",
    dedent(
        """
        """ + '"""add monitored customers and optional HelpDesk binding\n\nRevision ID: d2f4a6b8c010\nRevises: 8c1f2a6d9b40\nCreate Date: 2026-08-03 02:15:00\n\n"""' + """
        from typing import Sequence, Union

        from alembic import op
        import sqlalchemy as sa

        revision: str = "d2f4a6b8c010"
        down_revision: Union[str, Sequence[str], None] = "8c1f2a6d9b40"
        branch_labels: Union[str, Sequence[str], None] = None
        depends_on: Union[str, Sequence[str], None] = None


        def upgrade() -> None:
            op.alter_column(
                "customers",
                "external_requester_id",
                existing_type=sa.BigInteger(),
                nullable=True,
            )
            op.add_column(
                "customers",
                sa.Column(
                    "is_monitored",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("1"),
                ),
            )
            op.create_index(
                "ix_customers_is_monitored",
                "customers",
                ["is_monitored"],
                unique=False,
            )
            op.execute(
                sa.text(
                    "UPDATE ingestion_control SET cursor_position = 0, "
                    "worker_state = CASE WHEN enabled = 1 THEN 'IDLE' ELSE 'DISABLED' END"
                )
            )


        def downgrade() -> None:
            bind = op.get_bind()
            null_count = bind.execute(
                sa.text(
                    "SELECT COUNT(*) FROM customers "
                    "WHERE external_requester_id IS NULL"
                )
            ).scalar_one()
            if null_count:
                raise RuntimeError(
                    "Cannot downgrade while customers without external_requester_id exist"
                )
            op.drop_index("ix_customers_is_monitored", table_name="customers")
            op.drop_column("customers", "is_monitored")
            op.alter_column(
                "customers",
                "external_requester_id",
                existing_type=sa.BigInteger(),
                nullable=False,
            )
        """
    ),
)

# Unit tests for the new application behavior in the existing tests hierarchy.
write(
    "tests/application/use_cases/test_ticket_ingestion_use_case.py",
    dedent(
        """
        from __future__ import annotations

        import asyncio
        from datetime import datetime, timezone
        from types import SimpleNamespace
        from typing import cast
        from unittest.mock import AsyncMock
        from uuid import UUID

        from src.application.contracts.repositories import (
            CustomerRepository,
            SatisfactionRatingRepository,
            TagRepository,
            TicketRepository,
            TicketTagRepository,
        )
        from src.application.dtos.ingestion_control import IngestionControlState
        from src.application.dtos.ticket_ingestion import (
            IngestTicketBatchInput,
            TicketSourceRecord,
        )
        from src.application.use_cases.ingestion_control import IngestTicketBatch
        from src.domain.entities import CustomerEntity, TagEntity

        CUSTOMER_ID = UUID("0198f17c-1a23-7000-8000-000000000101")
        TICKET_ID = UUID("0198f17c-1a23-7000-8000-000000000102")
        TAG_ID = UUID("0198f17c-1a23-7000-8000-000000000103")


        def _record(*, email: str, ticket_id: int, requester_id: int) -> TicketSourceRecord:
            return TicketSourceRecord(
                ticket_id=ticket_id,
                subject="Falha de login",
                description="Erro ao autenticar",
                status="open",
                priority="high",
                requester_id=requester_id,
                requester_name="Cliente",
                requester_email=email,
                assignee_id=91,
                assignee_name="Atendente",
                created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 7, 1, 1, tzinfo=timezone.utc),
                first_response_at=datetime(2026, 7, 1, 0, 10, tzinfo=timezone.utc),
                tags=["login"],
            )


        def test_ingestion_only_imports_registered_customers_and_batches_writes() -> None:
            asyncio.run(_run_ingestion())


        async def _run_ingestion() -> None:
            customer = CustomerEntity(
                id=CUSTOMER_ID,
                requester_name="Cliente",
                requester_email="cliente@example.com",
                external_requester_id=None,
                is_monitored=True,
            )
            update_customers = AsyncMock()

            async def assign_ticket_ids(tickets):
                for ticket in tickets:
                    ticket.id = TICKET_ID

            insert_many = AsyncMock(side_effect=assign_ticket_ids)
            complete_cycle = AsyncMock()
            replace_many = AsyncMock()
            synchronize_many = AsyncMock()

            customer_repository = cast(
                CustomerRepository,
                SimpleNamespace(
                    find_monitored_by_emails=AsyncMock(
                        return_value={"cliente@example.com": customer}
                    ),
                    update_many=update_customers,
                ),
            )
            ticket_repository = cast(
                TicketRepository,
                SimpleNamespace(
                    get_ingestion_control=AsyncMock(
                        return_value=IngestionControlState(
                            enabled=True,
                            worker_state="IDLE",
                            cursor_position=0,
                        )
                    ),
                    get_by_external_ids=AsyncMock(return_value={}),
                    insert_many=insert_many,
                    update_many=AsyncMock(),
                    complete_ingestion_cycle=complete_cycle,
                ),
            )
            tag_repository = cast(
                TagRepository,
                SimpleNamespace(
                    resolve_by_names=AsyncMock(
                        return_value={"login": TagEntity(id=TAG_ID, name="login")}
                    )
                ),
            )
            ticket_tag_repository = cast(
                TicketTagRepository,
                SimpleNamespace(replace_many=replace_many),
            )
            satisfaction_repository = cast(
                SatisfactionRatingRepository,
                SimpleNamespace(synchronize_many=synchronize_many),
            )

            output = await IngestTicketBatch(
                customer_repository=customer_repository,
                ticket_repository=ticket_repository,
                tag_repository=tag_repository,
                ticket_tag_repository=ticket_tag_repository,
                satisfaction_repository=satisfaction_repository,
            ).execute(
                IngestTicketBatchInput(
                    expected_cursor=0,
                    source_total=2,
                    records=[
                        _record(
                            email="cliente@example.com",
                            ticket_id=1001,
                            requester_id=55,
                        ),
                        _record(
                            email="nao-cadastrado@example.com",
                            ticket_id=1002,
                            requester_id=56,
                        ),
                    ],
                )
            )

            assert output.received == 2
            assert output.matched_customers == 1
            assert output.ignored_unmonitored == 1
            assert output.tickets_created == 1
            assert output.next_cursor == 0
            assert customer.external_requester_id == 55
            update_customers.assert_awaited_once()
            insert_many.assert_awaited_once()
            replace_many.assert_awaited_once_with({TICKET_ID: [TAG_ID]})
            synchronize_many.assert_awaited_once_with({TICKET_ID: None})
            complete_cycle.assert_awaited_once_with(next_cursor=0)
        """
    ),
)

# README: replace the old source-authority description and document demo records.
readme = read("README.md")
readme = readme.replace(
    "Aplicação web para gerenciar clientes, simular respostas de uma plataforma de HelpDesk, persistir as relações no MySQL e calcular métricas comportamentais de atendimento.",
    "Aplicação web para gerenciar os clientes monitorados, cruzar seus e-mails com uma fonte JSON estática de HelpDesk, persistir tickets no MySQL e calcular métricas comportamentais de atendimento.",
)
readme = re.sub(
    r"## Fonte simulada de tickets.*?## Arquitetura",
    dedent(
        """
        ## Fonte estática de tickets

        O worker consome `data/tickets.json`, versionado no repositório. O arquivo representa o retorno estático de uma plataforma de HelpDesk e não é regenerado durante a execução.

        O fluxo é:

        ```text
        worker
          -> carrega e valida o JSON uma vez
          -> seleciona um lote pelo cursor persistido
          -> abre uma Unit of Work curta
          -> chama IngestTicketBatch
          -> o caso de uso cruza somente e-mails de clientes monitorados
          -> repositories consultam e persistem clientes, tickets, tags e avaliações em lote
          -> o cursor percorre circularmente a fonte estática
        ```

        O percurso circular permite que um cliente cadastrado depois da primeira leitura seja reconhecido em uma rodada posterior, sem criar clientes automaticamente a partir da fonte.

        Clientes disponíveis no arquivo de demonstração:

        - `ana.fernandes@techcorp.com.br` (`requester_id` 44521)
        - `bruno.silva@lojaviva.com.br` (`requester_id` 44522)
        - `camila.rocha@nexustech.com.br` (`requester_id` 44523)

        O ID externo é opcional no cadastro. Quando ausente, a primeira correspondência válida por e-mail vincula o `requester_id` da fonte ao cliente.

        ## Arquitetura
        """
    ).strip() + "\n\n",
    readme,
    count=1,
    flags=re.DOTALL,
)
readme = readme.replace(
    "MOCK_CUSTOMER_COUNT=500\nMOCK_START_TICKET_ID=100001\nMOCK_YEAR=2026\nMOCK_SEED=hostgator-challenge-v4\n",
    "",
)
readme = readme.replace(
    "5. cria ou reutiliza os clientes pelo e-mail e pelo ID externo;\n6. cria ou atualiza tickets de forma idempotente;\n7. sincroniza tags e avaliações;\n8. atualiza o total gerado na mesma transação;\n9. aguarda 30 segundos e inicia outra rodada.",
    "5. busca em lote somente os clientes monitorados pelos e-mails do lote;\n6. ignora solicitantes não cadastrados e conflitos de identidade;\n7. cria ou atualiza tickets de forma idempotente e em lote;\n8. sincroniza tags e avaliações em lote;\n9. atualiza o cursor na mesma transação;\n10. aguarda 30 segundos e inicia outra rodada.",
)
readme = readme.replace(
    "A ingestão também realiza upsert dos clientes presentes no retorno simulado do HelpDesk. O e-mail normalizado e o identificador externo protegem a identidade do cliente e permitem associar seus tickets.",
    "A ingestão nunca cria clientes a partir do JSON. O CRUD define a base monitorada; o e-mail normalizado realiza o cruzamento. A exclusão desativa o monitoramento e preserva o histórico de tickets.",
)
write("README.md", readme)

# Remove the one-shot automation artifacts from the resulting implementation commit.
for transient in (
    ROOT / "apply_ingestion_refactor.py",
    ROOT / ".github/workflows/apply-ingestion-refactor.yml",
):
    transient.unlink(missing_ok=True)
