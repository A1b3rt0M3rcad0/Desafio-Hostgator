import base64
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
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
        updated = False
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
                updated = True

        await self._session.flush()
        return CustomerSourceResult(
            customer=CustomerEntity.model_validate(customer),
            created=created,
            updated=updated,
        )


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
            updated=not created,
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

    async def mark_ingestion_processing(self) -> None:
        control = await self._get_ingestion_control_model(for_update=True)
        control.worker_state = "PROCESSING"
        control.last_heartbeat_at = self._now()
        control.last_error = None
        await self._session.flush()

    async def complete_ingestion_cycle(
        self,
        *,
        next_cursor: int,
        source_version: str,
    ) -> None:
        control = await self._get_ingestion_control_model(for_update=True)
        now = self._now()
        control.cursor_position = next_cursor
        control.source_version = source_version
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
