from __future__ import annotations

import base64
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, delete, exists, func, literal_column, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.contracts.repositories import (
    AuthSessionRepository,
    CustomerRepository,
    SatisfactionRatingRepository,
    TagRepository,
    TicketRepository,
    TicketTagRepository,
    UserRepository,
)
from src.application.dtos.analytics import (
    AnalyticsFilters,
    AssigneeFilterOption,
    CustomerAnalyticsQueryPage,
    CustomerAnalyticsRow,
    CustomerFilterOption,
    CustomerMetricsInput,
    DashboardOperationalSnapshot,
    DashboardPeriodSnapshot,
    ExportTicketRecord,
    PriorityAggregate,
    ResponseBucketAggregate,
    SatisfactionExportRecord,
    StatusAggregate,
    TagFilterOption,
    TimelineAggregate,
    TopCustomerAggregate,
    TopicAggregate,
    TopicCount,
)
from src.application.dtos.cursor_page import CursorPage
from src.application.dtos.ingestion_control import IngestionControlState
from src.application.dtos.ticket_ingestion import (
    CustomerSourceResult,
    SatisfactionSourceRecord,
    TicketSourceRecord,
    TicketSourceResult,
)
from src.domain.analytics import RATED_SATISFACTION_SCORES, RESOLVED_STATUSES
from src.domain.entities import (
    AuthSessionEntity,
    CustomerEntity,
    SatisfactionRatingEntity,
    TagEntity,
    TicketEntity,
    TicketTagEntity,
    UserEntity,
)
from src.infra.database.models import (
    AuthSession,
    Customer,
    IngestionControl,
    SatisfactionRating,
    Tag,
    Ticket,
    TicketTag,
    User,
)
from src.infra.database.unit_of_work import UnitOfWork


def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _enum_value(value: Any) -> str:
    return str(value.value if isinstance(value, Enum) else value)


class _SqlAlchemyRepository:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    @property
    def _session(self) -> AsyncSession:
        return self._unit_of_work.session


class SqlAlchemyUserRepository(_SqlAlchemyRepository, UserRepository):
    async def add(self, entity: UserEntity) -> None:
        orm = User(**entity.model_dump(exclude={"id", "created_at", "updated_at"}))
        self._session.add(orm)
        await self._session.flush()
        entity.id = orm.id
        entity.created_at = orm.created_at
        entity.updated_at = orm.updated_at

    async def get(self, entity_id: UUID) -> UserEntity | None:
        orm = await self._session.get(User, entity_id)
        return UserEntity.model_validate(orm) if orm else None

    async def get_by_email(self, email: str) -> UserEntity | None:
        result = await self._session.execute(select(User).where(User.email == email))
        orm = result.scalar_one_or_none()
        return UserEntity.model_validate(orm) if orm else None

    async def update(self, entity: UserEntity) -> None:
        orm = await self._session.get(User, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(
            exclude={"id", "created_at", "updated_at"}
        ).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(User, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(
        self,
        cursor: str | None,
        page_size: int = 20,
    ) -> CursorPage[UserEntity]:
        stmt = select(User).order_by(User.id).limit(page_size + 1)
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(User.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [UserEntity.model_validate(row) for row in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = (
            base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode()
            if has_next and entities
            else None
        )
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )


class SqlAlchemyAuthSessionRepository(_SqlAlchemyRepository, AuthSessionRepository):
    async def add(self, entity: AuthSessionEntity) -> None:
        orm = AuthSession(**entity.model_dump(exclude={"created_at", "updated_at"}))
        self._session.add(orm)
        await self._session.flush()
        entity.created_at = orm.created_at
        entity.updated_at = orm.updated_at

    async def get_for_update(self, session_id: UUID) -> AuthSessionEntity | None:
        result = await self._session.execute(
            select(AuthSession)
            .where(AuthSession.id == session_id)
            .with_for_update()
        )
        orm = result.scalar_one_or_none()
        return AuthSessionEntity.model_validate(orm) if orm else None

    async def update(self, entity: AuthSessionEntity) -> None:
        orm = await self._session.get(AuthSession, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(
            exclude={"id", "created_at", "updated_at"}
        ).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def revoke_all_by_user(self, user_id: UUID) -> int:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = await self._session.execute(
            update(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self._session.flush()
        return result.rowcount or 0


class SqlAlchemyCustomerRepository(_SqlAlchemyRepository, CustomerRepository):
    async def add(self, entity: CustomerEntity) -> None:
        orm = Customer(**entity.model_dump(exclude={"id", "created_at", "updated_at"}))
        self._session.add(orm)
        await self._session.flush()

    async def get(self, entity_id: UUID) -> CustomerEntity | None:
        orm = await self._session.get(Customer, entity_id)
        return CustomerEntity.model_validate(orm) if orm else None

    async def update(self, entity: CustomerEntity) -> None:
        orm = await self._session.get(Customer, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(
            exclude={"id", "created_at", "updated_at"}
        ).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(Customer, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(
        self,
        cursor: str | None,
        page_size: int = 20,
    ) -> CursorPage[CustomerEntity]:
        stmt = select(Customer).order_by(Customer.id).limit(page_size + 1)
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(Customer.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [CustomerEntity.model_validate(row) for row in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = (
            base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode()
            if has_next and entities
            else None
        )
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )

    async def upsert_from_source(
        self,
        *,
        external_requester_id: int,
        requester_name: str,
        requester_email: str,
    ) -> CustomerSourceResult:
        email = requester_email.strip().lower()
        rows = (
            await self._session.execute(
                select(Customer)
                .where(
                    or_(
                        func.lower(Customer.requester_email) == email,
                        Customer.external_requester_id == external_requester_id,
                    )
                )
                .with_for_update()
            )
        ).scalars().all()

        email_match = next(
            (
                customer
                for customer in rows
                if customer.requester_email.strip().lower() == email
            ),
            None,
        )
        id_match = next(
            (
                customer
                for customer in rows
                if customer.external_requester_id == external_requester_id
            ),
            None,
        )
        if (
            email_match is not None
            and id_match is not None
            and email_match.id != id_match.id
        ):
            raise ValueError(
                "Requester email and external ID belong to different customers"
            )

        customer = email_match or id_match
        created = False
        if customer is None:
            customer = Customer(
                external_requester_id=external_requester_id,
                requester_name=requester_name,
                requester_email=email,
            )
            self._session.add(customer)
            created = True
        else:
            if (
                customer.external_requester_id != external_requester_id
                or customer.requester_email.strip().lower() != email
            ):
                raise ValueError(
                    "Requester identity conflicts with an existing customer"
                )
            if customer.requester_name != requester_name:
                customer.requester_name = requester_name

        await self._session.flush()
        return CustomerSourceResult(
            customer=CustomerEntity.model_validate(customer),
            created=created,
        )

    async def list_filter_options(self) -> list[CustomerFilterOption]:
        rows = (
            await self._session.execute(
                select(
                    Customer.id,
                    Customer.requester_name,
                    Customer.requester_email,
                ).order_by(Customer.requester_name.asc(), Customer.requester_email.asc())
            )
        ).all()
        return [
            CustomerFilterOption(
                id=customer_id,
                requester_name=requester_name,
                requester_email=requester_email,
            )
            for customer_id, requester_name, requester_email in rows
        ]


class SqlAlchemyTicketRepository(_SqlAlchemyRepository, TicketRepository):
    async def add(self, entity: TicketEntity) -> None:
        orm = Ticket(**entity.model_dump(exclude={"id", "created_at", "updated_at"}))
        self._session.add(orm)
        await self._session.flush()

    async def get(self, entity_id: UUID) -> TicketEntity | None:
        orm = await self._session.get(Ticket, entity_id)
        return TicketEntity.model_validate(orm) if orm else None

    async def update(self, entity: TicketEntity) -> None:
        orm = await self._session.get(Ticket, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(
            exclude={"id", "created_at", "updated_at"}
        ).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(Ticket, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(
        self,
        cursor: str | None,
        page_size: int = 20,
    ) -> CursorPage[TicketEntity]:
        stmt = select(Ticket).order_by(Ticket.id).limit(page_size + 1)
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(Ticket.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [TicketEntity.model_validate(row) for row in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = (
            base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode()
            if has_next and entities
            else None
        )
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )

    async def page_by_tag_ids(
        self,
        tag_ids: list[UUID],
        cursor: str | None = None,
        page_size: int = 20,
    ) -> CursorPage[TicketEntity]:
        stmt = (
            select(Ticket)
            .join(TicketTag, Ticket.id == TicketTag.ticket_id)
            .where(TicketTag.tag_id.in_(tag_ids))
            .distinct()
            .order_by(Ticket.id)
            .limit(page_size + 1)
        )
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(Ticket.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [TicketEntity.model_validate(row) for row in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = (
            base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode()
            if has_next and entities
            else None
        )
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )

    async def upsert_from_source(
        self,
        record: TicketSourceRecord,
        *,
        customer_id: UUID,
    ) -> TicketSourceResult:
        ticket = (
            await self._session.execute(
                select(Ticket)
                .where(Ticket.external_ticket_id == record.ticket_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        source_updated_at = _naive_utc(record.updated_at)

        if ticket is not None and ticket.source_updated_at >= source_updated_at:
            return TicketSourceResult(
                ticket=TicketEntity.model_validate(ticket),
                unchanged=True,
            )

        values = {
            "customer_id": customer_id,
            "subject": record.subject,
            "description": record.description,
            "first_response_at": _naive_utc(record.first_response_at),
            "status": record.status,
            "priority": record.priority,
            "assignee_external_id": record.assignee_id,
            "assignee_name": record.assignee_name,
            "source_created_at": _naive_utc(record.created_at),
            "source_updated_at": source_updated_at,
        }
        created = ticket is None
        if ticket is None:
            ticket = Ticket(external_ticket_id=record.ticket_id, **values)
            self._session.add(ticket)
        else:
            for key, value in values.items():
                setattr(ticket, key, value)

        await self._session.flush()
        return TicketSourceResult(
            ticket=TicketEntity.model_validate(ticket),
            created=created,
        )

    async def get_ingestion_control(
        self,
        *,
        for_update: bool = False,
    ) -> IngestionControlState:
        control = await self._get_ingestion_control_model(for_update=for_update)
        return self._to_ingestion_control_state(control)

    async def set_ingestion_enabled(
        self,
        enabled: bool,
    ) -> IngestionControlState:
        control = await self._get_ingestion_control_model(for_update=True)
        control.enabled = enabled
        control.worker_state = "IDLE" if enabled else "DISABLED"
        if enabled:
            control.last_error = None
        await self._session.flush()
        return self._to_ingestion_control_state(control)

    async def complete_ingestion_cycle(self, *, next_cursor: int) -> None:
        control = await self._get_ingestion_control_model(for_update=True)
        now = self._now()
        control.cursor_position = next_cursor
        control.worker_state = "IDLE"
        control.last_heartbeat_at = now
        control.last_success_at = now
        control.last_error = None
        await self._session.flush()

    async def register_ingestion_error(self, message: str) -> None:
        control = await self._get_ingestion_control_model(for_update=True)
        control.worker_state = "ERROR"
        control.last_heartbeat_at = self._now()
        control.last_error = message[:2000]
        await self._session.flush()

    async def get_dashboard_period_snapshot(
        self,
        filters: AnalyticsFilters,
        top_topics_limit: int,
    ) -> DashboardPeriodSnapshot:
        predicates = self._ticket_predicates(filters)
        valid_response = and_(
            Ticket.first_response_at.is_not(None),
            Ticket.first_response_at >= Ticket.source_created_at,
        )
        valid_response_seconds = case(
            (
                valid_response,
                self._seconds_between(
                    Ticket.first_response_at,
                    Ticket.source_created_at,
                ),
            ),
            else_=None,
        )
        summary = (
            await self._session.execute(
                select(
                    func.count(Ticket.id).label("total_tickets"),
                    func.sum(
                        case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)
                    ).label("resolved_tickets"),
                    func.avg(valid_response_seconds).label(
                        "average_first_response_seconds"
                    ),
                    func.sum(case((valid_response, 1), else_=0)).label(
                        "responded_tickets"
                    ),
                    func.sum(
                        case((SatisfactionRating.score == "GOOD", 1), else_=0)
                    ).label("good_ratings"),
                    func.sum(
                        case((SatisfactionRating.score == "BAD", 1), else_=0)
                    ).label("bad_ratings"),
                )
                .select_from(Ticket)
                .outerjoin(
                    SatisfactionRating,
                    SatisfactionRating.ticket_id == Ticket.id,
                )
                .where(*predicates)
            )
        ).mappings().one()

        ordered_tickets = (
            select(
                Ticket.customer_id.label("customer_id"),
                Ticket.source_created_at.label("current_at"),
                func.lag(Ticket.source_created_at)
                .over(
                    partition_by=Ticket.customer_id,
                    order_by=(Ticket.source_created_at, Ticket.id),
                )
                .label("previous_at"),
            )
            .where(*predicates)
            .subquery()
        )
        recurrence = (
            await self._session.execute(
                select(
                    func.avg(
                        self._seconds_between(
                            ordered_tickets.c.current_at,
                            ordered_tickets.c.previous_at,
                        )
                    ).label("average_seconds"),
                    func.count(ordered_tickets.c.previous_at).label(
                        "sample_intervals"
                    ),
                    func.count(
                        func.distinct(ordered_tickets.c.customer_id)
                    ).label("customers"),
                ).where(ordered_tickets.c.previous_at.is_not(None))
            )
        ).mappings().one()

        status_rows = (
            await self._session.execute(
                select(
                    Ticket.status.label("label"),
                    func.count(Ticket.id).label("value"),
                )
                .where(*predicates)
                .group_by(Ticket.status)
                .order_by(func.count(Ticket.id).desc())
            )
        ).mappings().all()

        priority_rows = (
            await self._session.execute(
                select(
                    Ticket.priority.label("priority"),
                    func.count(Ticket.id).label("ticket_count"),
                    func.sum(
                        case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)
                    ).label("resolved_tickets"),
                    func.avg(valid_response_seconds).label(
                        "average_first_response_seconds"
                    ),
                )
                .where(*predicates)
                .group_by(Ticket.priority)
                .order_by(func.count(Ticket.id).desc())
            )
        ).mappings().all()

        topic_rows = (
            await self._session.execute(
                select(
                    Tag.name.label("tag"),
                    func.count(func.distinct(Ticket.id)).label("ticket_count"),
                    func.sum(
                        case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)
                    ).label("resolved_tickets"),
                    func.avg(valid_response_seconds).label(
                        "average_first_response_seconds"
                    ),
                )
                .select_from(Ticket)
                .join(TicketTag, TicketTag.ticket_id == Ticket.id)
                .join(Tag, Tag.id == TicketTag.tag_id)
                .where(*predicates)
                .group_by(Tag.id, Tag.name)
                .order_by(
                    func.count(func.distinct(Ticket.id)).desc(),
                    Tag.name.asc(),
                )
                .limit(top_topics_limit)
            )
        ).mappings().all()

        return DashboardPeriodSnapshot(
            total_tickets=int(summary["total_tickets"] or 0),
            resolved_tickets=int(summary["resolved_tickets"] or 0),
            average_first_response_seconds=self._optional_float(
                summary["average_first_response_seconds"]
            ),
            responded_tickets=int(summary["responded_tickets"] or 0),
            good_ratings=int(summary["good_ratings"] or 0),
            bad_ratings=int(summary["bad_ratings"] or 0),
            average_recurrence_seconds=self._optional_float(
                recurrence["average_seconds"]
            ),
            recurrence_sample_intervals=int(recurrence["sample_intervals"] or 0),
            customers_with_recurrence=int(recurrence["customers"] or 0),
            status_counts=[
                StatusAggregate(
                    label=_enum_value(row["label"]),
                    value=int(row["value"] or 0),
                )
                for row in status_rows
            ],
            priority_aggregates=[
                PriorityAggregate(
                    priority=_enum_value(row["priority"]),
                    ticket_count=int(row["ticket_count"] or 0),
                    resolved_tickets=int(row["resolved_tickets"] or 0),
                    average_first_response_seconds=self._optional_float(
                        row["average_first_response_seconds"]
                    ),
                )
                for row in priority_rows
            ],
            topic_aggregates=[
                TopicAggregate(
                    tag=row["tag"],
                    ticket_count=int(row["ticket_count"] or 0),
                    resolved_tickets=int(row["resolved_tickets"] or 0),
                    average_first_response_seconds=self._optional_float(
                        row["average_first_response_seconds"]
                    ),
                )
                for row in topic_rows
            ],
        )

    async def get_dashboard_operational_snapshot(
        self,
        filters: AnalyticsFilters,
        timeline_limit: int,
    ) -> DashboardOperationalSnapshot:
        predicates = self._ticket_predicates(filters)
        valid_response = and_(
            Ticket.first_response_at.is_not(None),
            Ticket.first_response_at >= Ticket.source_created_at,
        )
        valid_response_seconds = case(
            (
                valid_response,
                self._seconds_between(
                    Ticket.first_response_at,
                    Ticket.source_created_at,
                ),
            ),
            else_=None,
        )

        timeline_rows = list(
            reversed(
                (
                    await self._session.execute(
                        select(
                            func.date(Ticket.source_created_at).label("date"),
                            func.count(Ticket.id).label("opened"),
                            func.sum(
                                case(
                                    (Ticket.status.in_(RESOLVED_STATUSES), 1),
                                    else_=0,
                                )
                            ).label("resolved"),
                            func.avg(valid_response_seconds).label(
                                "average_first_response_seconds"
                            ),
                            func.sum(
                                case(
                                    (SatisfactionRating.score == "GOOD", 1),
                                    else_=0,
                                )
                            ).label("good_ratings"),
                            func.sum(
                                case(
                                    (SatisfactionRating.score == "BAD", 1),
                                    else_=0,
                                )
                            ).label("bad_ratings"),
                        )
                        .select_from(Ticket)
                        .outerjoin(
                            SatisfactionRating,
                            SatisfactionRating.ticket_id == Ticket.id,
                        )
                        .where(*predicates)
                        .group_by(func.date(Ticket.source_created_at))
                        .order_by(func.date(Ticket.source_created_at).desc())
                        .limit(timeline_limit)
                    )
                ).mappings().all()
            )
        )

        response_seconds = self._seconds_between(
            Ticket.first_response_at,
            Ticket.source_created_at,
        )
        response_bucket = case(
            (
                or_(
                    Ticket.first_response_at.is_(None),
                    Ticket.first_response_at < Ticket.source_created_at,
                ),
                "unanswered",
            ),
            (response_seconds <= 15 * 60, "up_to_15m"),
            (response_seconds <= 30 * 60, "15_to_30m"),
            (response_seconds <= 60 * 60, "30_to_60m"),
            (response_seconds <= 4 * 60 * 60, "1_to_4h"),
            else_="over_4h",
        ).label("bucket")
        response_rows = (
            await self._session.execute(
                select(response_bucket, func.count(Ticket.id).label("ticket_count"))
                .where(*predicates)
                .group_by(response_bucket)
            )
        ).mappings().all()

        per_customer = (
            select(
                Ticket.customer_id.label("customer_id"),
                func.count(Ticket.id).label("ticket_count"),
            )
            .where(*predicates)
            .group_by(Ticket.customer_id)
            .subquery()
        )
        behavior = (
            await self._session.execute(
                select(
                    func.count(per_customer.c.customer_id).label("unique_customers"),
                    func.sum(
                        case((per_customer.c.ticket_count > 1, 1), else_=0)
                    ).label("repeat_customers"),
                    func.avg(per_customer.c.ticket_count).label(
                        "average_tickets_per_customer"
                    ),
                )
            )
        ).mappings().one()

        top_customer_rows = (
            await self._session.execute(
                select(
                    Customer.id.label("customer_id"),
                    Customer.requester_name,
                    Customer.requester_email,
                    func.count(Ticket.id).label("ticket_count"),
                )
                .select_from(Ticket)
                .join(Customer, Customer.id == Ticket.customer_id)
                .where(*predicates)
                .group_by(
                    Customer.id,
                    Customer.requester_name,
                    Customer.requester_email,
                )
                .order_by(func.count(Ticket.id).desc(), Customer.requester_name.asc())
                .limit(5)
            )
        ).mappings().all()

        return DashboardOperationalSnapshot(
            timeline=[
                TimelineAggregate(
                    date=str(row["date"]),
                    opened=int(row["opened"] or 0),
                    resolved=int(row["resolved"] or 0),
                    average_first_response_seconds=self._optional_float(
                        row["average_first_response_seconds"]
                    ),
                    good_ratings=int(row["good_ratings"] or 0),
                    bad_ratings=int(row["bad_ratings"] or 0),
                )
                for row in timeline_rows
            ],
            response_buckets=[
                ResponseBucketAggregate(
                    bucket=row["bucket"],
                    ticket_count=int(row["ticket_count"] or 0),
                )
                for row in response_rows
            ],
            unique_customers=int(behavior["unique_customers"] or 0),
            repeat_customers=int(behavior["repeat_customers"] or 0),
            average_tickets_per_customer=self._optional_float(
                behavior["average_tickets_per_customer"]
            ),
            top_customers=[
                TopCustomerAggregate(
                    customer_id=row["customer_id"],
                    requester_name=row["requester_name"],
                    requester_email=row["requester_email"],
                    ticket_count=int(row["ticket_count"] or 0),
                )
                for row in top_customer_rows
            ],
        )

    async def page_customer_analytics(
        self,
        input_dto: CustomerMetricsInput,
    ) -> CustomerAnalyticsQueryPage:
        predicates = self._ticket_predicates(input_dto)
        customer_ids_subquery = (
            select(Ticket.customer_id.label("customer_id"))
            .where(*predicates)
            .group_by(Ticket.customer_id)
            .subquery()
        )
        total_customers = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(customer_ids_subquery)
                )
            ).scalar_one()
            or 0
        )
        offset = (input_dto.page - 1) * input_dto.page_size
        valid_response = and_(
            Ticket.first_response_at.is_not(None),
            Ticket.first_response_at >= Ticket.source_created_at,
        )
        base_rows = (
            await self._session.execute(
                select(
                    Customer.id.label("customer_id"),
                    Customer.external_requester_id,
                    Customer.requester_name,
                    Customer.requester_email,
                    func.count(Ticket.id).label("ticket_volume"),
                    func.sum(
                        case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)
                    ).label("resolved_tickets"),
                    func.avg(
                        case(
                            (
                                valid_response,
                                self._seconds_between(
                                    Ticket.first_response_at,
                                    Ticket.source_created_at,
                                ),
                            ),
                            else_=None,
                        )
                    ).label("average_first_response_seconds"),
                )
                .select_from(Ticket)
                .join(Customer, Customer.id == Ticket.customer_id)
                .where(*predicates)
                .group_by(
                    Customer.id,
                    Customer.external_requester_id,
                    Customer.requester_name,
                    Customer.requester_email,
                )
                .order_by(func.count(Ticket.id).desc(), Customer.requester_name.asc())
                .offset(offset)
                .limit(input_dto.page_size)
            )
        ).mappings().all()
        page_customer_ids = [row["customer_id"] for row in base_rows]
        if not page_customer_ids:
            return CustomerAnalyticsQueryPage(
                items=[],
                page=input_dto.page,
                page_size=input_dto.page_size,
                total=total_customers,
                has_next=False,
                has_previous=input_dto.page > 1,
            )

        satisfaction_rows = (
            await self._session.execute(
                select(
                    Ticket.customer_id,
                    func.sum(
                        case((SatisfactionRating.score == "GOOD", 1), else_=0)
                    ).label("good_ratings"),
                    func.sum(
                        case((SatisfactionRating.score == "BAD", 1), else_=0)
                    ).label("bad_ratings"),
                )
                .select_from(Ticket)
                .join(
                    SatisfactionRating,
                    SatisfactionRating.ticket_id == Ticket.id,
                )
                .where(
                    *predicates,
                    Ticket.customer_id.in_(page_customer_ids),
                    SatisfactionRating.score.in_(RATED_SATISFACTION_SCORES),
                )
                .group_by(Ticket.customer_id)
            )
        ).mappings().all()
        satisfaction_by_customer = {
            row["customer_id"]: row for row in satisfaction_rows
        }

        ordered = (
            select(
                Ticket.customer_id.label("customer_id"),
                Ticket.source_created_at.label("current_at"),
                func.lag(Ticket.source_created_at)
                .over(
                    partition_by=Ticket.customer_id,
                    order_by=(Ticket.source_created_at, Ticket.id),
                )
                .label("previous_at"),
            )
            .where(*predicates, Ticket.customer_id.in_(page_customer_ids))
            .subquery()
        )
        recurrence_rows = (
            await self._session.execute(
                select(
                    ordered.c.customer_id,
                    func.avg(
                        self._seconds_between(
                            ordered.c.current_at,
                            ordered.c.previous_at,
                        )
                    ).label("average_seconds"),
                    func.count(ordered.c.previous_at).label("sample_intervals"),
                )
                .where(ordered.c.previous_at.is_not(None))
                .group_by(ordered.c.customer_id)
            )
        ).mappings().all()
        recurrence_by_customer = {row["customer_id"]: row for row in recurrence_rows}

        topic_rows = (
            await self._session.execute(
                select(
                    Ticket.customer_id,
                    Tag.name.label("tag"),
                    func.count(func.distinct(Ticket.id)).label("ticket_count"),
                )
                .select_from(Ticket)
                .join(TicketTag, TicketTag.ticket_id == Ticket.id)
                .join(Tag, Tag.id == TicketTag.tag_id)
                .where(*predicates, Ticket.customer_id.in_(page_customer_ids))
                .group_by(Ticket.customer_id, Tag.id, Tag.name)
                .order_by(
                    Ticket.customer_id.asc(),
                    func.count(func.distinct(Ticket.id)).desc(),
                    Tag.name.asc(),
                )
            )
        ).mappings().all()
        topics_by_customer: dict[UUID, list[TopicCount]] = defaultdict(list)
        for row in topic_rows:
            bucket = topics_by_customer[row["customer_id"]]
            if len(bucket) < input_dto.top_topics_limit:
                bucket.append(
                    TopicCount(
                        tag=row["tag"],
                        ticket_count=int(row["ticket_count"] or 0),
                    )
                )

        items: list[CustomerAnalyticsRow] = []
        for row in base_rows:
            customer_id = row["customer_id"]
            satisfaction = satisfaction_by_customer.get(customer_id, {})
            recurrence = recurrence_by_customer.get(customer_id, {})
            items.append(
                CustomerAnalyticsRow(
                    customer_id=customer_id,
                    external_requester_id=row["external_requester_id"],
                    requester_name=row["requester_name"],
                    requester_email=row["requester_email"],
                    ticket_volume=int(row["ticket_volume"] or 0),
                    resolved_tickets=int(row["resolved_tickets"] or 0),
                    good_ratings=int(satisfaction.get("good_ratings") or 0),
                    bad_ratings=int(satisfaction.get("bad_ratings") or 0),
                    average_first_response_seconds=self._optional_float(
                        row["average_first_response_seconds"]
                    ),
                    average_recurrence_seconds=self._optional_float(
                        recurrence.get("average_seconds")
                    ),
                    recurrence_sample_intervals=int(
                        recurrence.get("sample_intervals") or 0
                    ),
                    top_topics=topics_by_customer.get(customer_id, []),
                )
            )

        return CustomerAnalyticsQueryPage(
            items=items,
            page=input_dto.page,
            page_size=input_dto.page_size,
            total=total_customers,
            has_next=offset + len(items) < total_customers,
            has_previous=input_dto.page > 1,
        )

    async def list_assignee_options(self) -> list[AssigneeFilterOption]:
        rows = (
            await self._session.execute(
                select(Ticket.assignee_external_id, Ticket.assignee_name)
                .where(Ticket.assignee_external_id.is_not(None))
                .group_by(Ticket.assignee_external_id, Ticket.assignee_name)
                .order_by(Ticket.assignee_name.asc())
            )
        ).all()
        return [
            AssigneeFilterOption(external_id=external_id, name=name)
            for external_id, name in rows
        ]

    async def count_export_rows(self, filters: AnalyticsFilters) -> int:
        return int(
            (
                await self._session.execute(
                    select(func.count(Ticket.id)).where(
                        *self._ticket_predicates(filters)
                    )
                )
            ).scalar_one()
            or 0
        )

    async def fetch_export_records(
        self,
        filters: AnalyticsFilters,
        limit: int,
        offset: int,
    ) -> list[ExportTicketRecord]:
        rows = (
            await self._session.execute(
                select(
                    Ticket.id.label("internal_ticket_id"),
                    Ticket.external_ticket_id,
                    Ticket.subject,
                    Ticket.description,
                    Ticket.status,
                    Ticket.priority,
                    Ticket.assignee_external_id,
                    Ticket.assignee_name,
                    Ticket.source_created_at,
                    Ticket.source_updated_at,
                    Ticket.first_response_at,
                    Customer.external_requester_id,
                    Customer.requester_name,
                    Customer.requester_email,
                    SatisfactionRating.score.label("satisfaction_score"),
                    SatisfactionRating.offered_at,
                    SatisfactionRating.rated_at,
                    SatisfactionRating.comment,
                )
                .select_from(Ticket)
                .join(Customer, Customer.id == Ticket.customer_id)
                .outerjoin(
                    SatisfactionRating,
                    SatisfactionRating.ticket_id == Ticket.id,
                )
                .where(*self._ticket_predicates(filters))
                .order_by(Ticket.external_ticket_id.asc())
                .offset(offset)
                .limit(limit)
            )
        ).mappings().all()

        ticket_ids = [row["internal_ticket_id"] for row in rows]
        tags_by_ticket: dict[UUID, list[str]] = defaultdict(list)
        if ticket_ids:
            tag_rows = (
                await self._session.execute(
                    select(TicketTag.ticket_id, Tag.name)
                    .join(Tag, Tag.id == TicketTag.tag_id)
                    .where(TicketTag.ticket_id.in_(ticket_ids))
                    .order_by(TicketTag.ticket_id.asc(), Tag.name.asc())
                )
            ).all()
            for ticket_id, tag_name in tag_rows:
                tags_by_ticket[ticket_id].append(tag_name)

        records: list[ExportTicketRecord] = []
        for row in rows:
            rating = None
            if row["satisfaction_score"] is not None:
                rating = SatisfactionExportRecord(
                    score=_enum_value(row["satisfaction_score"]),
                    offered_at=row["offered_at"],
                    rated_at=row["rated_at"],
                    comment=row["comment"] or "",
                )
            records.append(
                ExportTicketRecord(
                    internal_ticket_id=row["internal_ticket_id"],
                    ticket_id=row["external_ticket_id"],
                    subject=row["subject"],
                    description=row["description"],
                    status=_enum_value(row["status"]),
                    priority=_enum_value(row["priority"]),
                    requester_id=row["external_requester_id"],
                    requester_name=row["requester_name"],
                    requester_email=row["requester_email"],
                    assignee_id=row["assignee_external_id"],
                    assignee_name=row["assignee_name"],
                    created_at=row["source_created_at"],
                    updated_at=row["source_updated_at"],
                    first_response_at=row["first_response_at"],
                    tags=tags_by_ticket.get(row["internal_ticket_id"], []),
                    satisfaction_rating=rating,
                )
            )
        return records

    def _ticket_predicates(self, filters: AnalyticsFilters) -> list[Any]:
        predicates: list[Any] = []
        if filters.from_at:
            predicates.append(Ticket.source_created_at >= _naive_utc(filters.from_at))
        if filters.to_at:
            predicates.append(Ticket.source_created_at <= _naive_utc(filters.to_at))
        if filters.customer_ids:
            predicates.append(Ticket.customer_id.in_(filters.customer_ids))
        if filters.requester_emails:
            predicates.append(
                exists(
                    select(literal_column("1"))
                    .select_from(Customer)
                    .where(
                        Customer.id == Ticket.customer_id,
                        func.lower(Customer.requester_email).in_(
                            filters.requester_emails
                        ),
                    )
                )
            )
        if filters.statuses:
            predicates.append(Ticket.status.in_(filters.statuses))
        if filters.priorities:
            predicates.append(Ticket.priority.in_(filters.priorities))
        if filters.assignee_external_ids:
            predicates.append(
                Ticket.assignee_external_id.in_(filters.assignee_external_ids)
            )
        if filters.tag_ids or filters.tag_names:
            tag_query = (
                select(literal_column("1"))
                .select_from(TicketTag)
                .join(Tag, Tag.id == TicketTag.tag_id)
                .where(TicketTag.ticket_id == Ticket.id)
            )
            tag_conditions: list[Any] = []
            if filters.tag_ids:
                tag_conditions.append(Tag.id.in_(filters.tag_ids))
            if filters.tag_names:
                tag_conditions.append(Tag.name.in_(filters.tag_names))
            predicates.append(exists(tag_query.where(*tag_conditions)))
        if filters.satisfaction_scores:
            predicates.append(
                exists(
                    select(literal_column("1"))
                    .select_from(SatisfactionRating)
                    .where(
                        SatisfactionRating.ticket_id == Ticket.id,
                        SatisfactionRating.score.in_(filters.satisfaction_scores),
                    )
                )
            )
        if filters.has_first_response is True:
            predicates.append(Ticket.first_response_at.is_not(None))
        elif filters.has_first_response is False:
            predicates.append(Ticket.first_response_at.is_(None))
        return predicates

    @staticmethod
    def _seconds_between(end_column: Any, start_column: Any) -> Any:
        return func.unix_timestamp(end_column) - func.unix_timestamp(start_column)

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        return round(float(value), 2) if value is not None else None

    async def _get_ingestion_control_model(
        self,
        *,
        for_update: bool = False,
    ) -> IngestionControl:
        stmt = select(IngestionControl).where(IngestionControl.id == 1)
        if for_update:
            stmt = stmt.with_for_update()
        control = (await self._session.execute(stmt)).scalar_one_or_none()
        if control is None:
            control = IngestionControl(id=1)
            self._session.add(control)
            await self._session.flush()
        return control

    @staticmethod
    def _to_ingestion_control_state(
        control: IngestionControl,
    ) -> IngestionControlState:
        return IngestionControlState(
            enabled=control.enabled,
            worker_state=control.worker_state,
            cursor_position=control.cursor_position,
            last_heartbeat_at=control.last_heartbeat_at,
            last_success_at=control.last_success_at,
            last_error=control.last_error,
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)


class SqlAlchemySatisfactionRatingRepository(
    _SqlAlchemyRepository,
    SatisfactionRatingRepository,
):
    async def add(self, entity: SatisfactionRatingEntity) -> None:
        orm = SatisfactionRating(
            **entity.model_dump(exclude={"id", "created_at", "updated_at"})
        )
        self._session.add(orm)
        await self._session.flush()

    async def get(self, entity_id: UUID) -> SatisfactionRatingEntity | None:
        orm = await self._session.get(SatisfactionRating, entity_id)
        return SatisfactionRatingEntity.model_validate(orm) if orm else None

    async def update(self, entity: SatisfactionRatingEntity) -> None:
        orm = await self._session.get(SatisfactionRating, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(
            exclude={"id", "created_at", "updated_at"}
        ).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(SatisfactionRating, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(
        self,
        cursor: str | None,
        page_size: int = 20,
    ) -> CursorPage[SatisfactionRatingEntity]:
        stmt = select(SatisfactionRating).order_by(SatisfactionRating.id).limit(
            page_size + 1
        )
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(SatisfactionRating.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [
            SatisfactionRatingEntity.model_validate(row) for row in rows[:page_size]
        ]
        has_next = len(rows) > page_size
        next_cursor = (
            base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode()
            if has_next and entities
            else None
        )
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )

    async def synchronize_from_source(
        self,
        *,
        ticket_id: UUID,
        source: SatisfactionSourceRecord | None,
    ) -> None:
        current = (
            await self._session.execute(
                select(SatisfactionRating)
                .where(SatisfactionRating.ticket_id == ticket_id)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if source is None:
            if current is not None:
                await self._session.delete(current)
                await self._session.flush()
            return

        values = {
            "score": source.score,
            "offered_at": _naive_utc(source.offered_at),
            "rated_at": _naive_utc(source.rated_at),
            "comment": source.comment,
        }
        if current is None:
            self._session.add(SatisfactionRating(ticket_id=ticket_id, **values))
        else:
            for key, value in values.items():
                setattr(current, key, value)
        await self._session.flush()


class SqlAlchemyTagRepository(_SqlAlchemyRepository, TagRepository):
    async def add(self, entity: TagEntity) -> None:
        orm = Tag(**entity.model_dump(exclude={"id", "created_at", "updated_at"}))
        self._session.add(orm)
        await self._session.flush()

    async def get(self, entity_id: UUID) -> TagEntity | None:
        orm = await self._session.get(Tag, entity_id)
        return TagEntity.model_validate(orm) if orm else None

    async def update(self, entity: TagEntity) -> None:
        orm = await self._session.get(Tag, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(
            exclude={"id", "created_at", "updated_at"}
        ).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(Tag, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(
        self,
        cursor: str | None,
        page_size: int = 20,
    ) -> CursorPage[TagEntity]:
        stmt = select(Tag).order_by(Tag.id).limit(page_size + 1)
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(Tag.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [TagEntity.model_validate(row) for row in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = (
            base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode()
            if has_next and entities
            else None
        )
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )

    async def resolve_by_names(self, names: list[str]) -> dict[str, TagEntity]:
        normalized_names = sorted({name.strip() for name in names if name.strip()})
        if not normalized_names:
            return {}

        existing = (
            await self._session.execute(
                select(Tag).where(Tag.name.in_(normalized_names))
            )
        ).scalars().all()
        by_name = {tag.name: tag for tag in existing}
        for name in normalized_names:
            if name not in by_name:
                tag = Tag(name=name)
                self._session.add(tag)
                by_name[name] = tag
        await self._session.flush()
        return {
            name: TagEntity.model_validate(tag)
            for name, tag in by_name.items()
        }

    async def list_filter_options(self) -> list[TagFilterOption]:
        rows = (
            await self._session.execute(
                select(Tag.id, Tag.name).order_by(Tag.name.asc())
            )
        ).all()
        return [TagFilterOption(id=tag_id, name=name) for tag_id, name in rows]


class SqlAlchemyTicketTagRepository(_SqlAlchemyRepository, TicketTagRepository):
    async def add(self, entity: TicketTagEntity) -> None:
        orm = TicketTag(
            **entity.model_dump(exclude={"id", "created_at", "updated_at"})
        )
        self._session.add(orm)
        await self._session.flush()

    async def delete_by_ticket_and_tag(
        self,
        ticket_id: UUID,
        tag_id: UUID,
    ) -> None:
        result = await self._session.execute(
            select(TicketTag).where(
                TicketTag.ticket_id == ticket_id,
                TicketTag.tag_id == tag_id,
            )
        )
        orm = result.scalar_one_or_none()
        if orm:
            await self._session.delete(orm)
            await self._session.flush()

    async def get(self, entity_id: UUID) -> TicketTagEntity | None:
        orm = await self._session.get(TicketTag, entity_id)
        return TicketTagEntity.model_validate(orm) if orm else None

    async def update(self, entity: TicketTagEntity) -> None:
        orm = await self._session.get(TicketTag, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(
            exclude={"id", "created_at", "updated_at"}
        ).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(TicketTag, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(
        self,
        cursor: str | None,
        page_size: int = 20,
    ) -> CursorPage[TicketTagEntity]:
        stmt = select(TicketTag).order_by(TicketTag.id).limit(page_size + 1)
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(TicketTag.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [TicketTagEntity.model_validate(row) for row in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = (
            base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode()
            if has_next and entities
            else None
        )
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )

    async def replace_for_ticket(
        self,
        *,
        ticket_id: UUID,
        tag_ids: list[UUID],
    ) -> None:
        await self._session.execute(
            delete(TicketTag).where(TicketTag.ticket_id == ticket_id)
        )
        for tag_id in dict.fromkeys(tag_ids):
            self._session.add(TicketTag(ticket_id=ticket_id, tag_id=tag_id))
        await self._session.flush()
