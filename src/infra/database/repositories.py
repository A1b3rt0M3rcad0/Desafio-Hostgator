import base64
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.contracts.repositories import (
    CustomerRepository,
    SatisfactionRatingRepository,
    TagRepository,
    TicketRepository,
    TicketTagRepository,
    UserRepository,
)
from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import (
    CustomerEntity,
    SatisfactionRatingEntity,
    TagEntity,
    TicketEntity,
    TicketTagEntity,
    UserEntity,
)
from src.infra.database.models import (
    Customer,
    SatisfactionRating,
    Tag,
    Ticket,
    TicketTag,
    User,
)
from src.infra.database.unit_of_work import UnitOfWork


class _SqlAlchemyRepository:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    @property
    def _session(self) -> AsyncSession:
        return self._unit_of_work.session


class SqlAlchemyUserRepository(_SqlAlchemyRepository, UserRepository):

    async def add(self, entity: UserEntity) -> None:
        orm = User(**entity.model_dump(exclude={'id', 'created_at', 'updated_at'}))
        self._session.add(orm)
        await self._session.flush()

    async def get(self, entity_id: UUID) -> UserEntity | None:
        orm = await self._session.get(User, entity_id)
        return UserEntity.model_validate(orm) if orm else None

    async def update(self, entity: UserEntity) -> None:
        orm = await self._session.get(User, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(exclude={'id', 'created_at', 'updated_at'}).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(User, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(self, cursor: str | None, page_size: int = 20) -> CursorPage[UserEntity]:
        stmt = select(User).order_by(User.id).limit(page_size + 1)
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(User.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [UserEntity.model_validate(r) for r in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode() if has_next and entities else None
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )


class SqlAlchemyCustomerRepository(_SqlAlchemyRepository, CustomerRepository):

    async def add(self, entity: CustomerEntity) -> None:
        orm = Customer(**entity.model_dump(exclude={'id', 'created_at', 'updated_at'}))
        self._session.add(orm)
        await self._session.flush()

    async def get(self, entity_id: UUID) -> CustomerEntity | None:
        orm = await self._session.get(Customer, entity_id)
        return CustomerEntity.model_validate(orm) if orm else None

    async def update(self, entity: CustomerEntity) -> None:
        orm = await self._session.get(Customer, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(exclude={'id', 'created_at', 'updated_at'}).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(Customer, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(self, cursor: str | None, page_size: int = 20) -> CursorPage[CustomerEntity]:
        stmt = select(Customer).order_by(Customer.id).limit(page_size + 1)
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(Customer.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [CustomerEntity.model_validate(r) for r in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode() if has_next and entities else None
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )


class SqlAlchemyTicketRepository(_SqlAlchemyRepository, TicketRepository):

    async def add(self, entity: TicketEntity) -> None:
        orm = Ticket(**entity.model_dump(exclude={'id', 'created_at', 'updated_at'}))
        self._session.add(orm)
        await self._session.flush()

    async def get(self, entity_id: UUID) -> TicketEntity | None:
        orm = await self._session.get(Ticket, entity_id)
        return TicketEntity.model_validate(orm) if orm else None

    async def update(self, entity: TicketEntity) -> None:
        orm = await self._session.get(Ticket, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(exclude={'id', 'created_at', 'updated_at'}).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(Ticket, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(self, cursor: str | None, page_size: int = 20) -> CursorPage[TicketEntity]:
        stmt = select(Ticket).order_by(Ticket.id).limit(page_size + 1)
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(Ticket.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [TicketEntity.model_validate(r) for r in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode() if has_next and entities else None
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
        entities = [TicketEntity.model_validate(r) for r in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode() if has_next and entities else None
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )


class SqlAlchemySatisfactionRatingRepository(
    _SqlAlchemyRepository,
    SatisfactionRatingRepository,
):

    async def add(self, entity: SatisfactionRatingEntity) -> None:
        orm = SatisfactionRating(**entity.model_dump(exclude={'id', 'created_at', 'updated_at'}))
        self._session.add(orm)
        await self._session.flush()

    async def get(self, entity_id: UUID) -> SatisfactionRatingEntity | None:
        orm = await self._session.get(SatisfactionRating, entity_id)
        return SatisfactionRatingEntity.model_validate(orm) if orm else None

    async def update(self, entity: SatisfactionRatingEntity) -> None:
        orm = await self._session.get(SatisfactionRating, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(exclude={'id', 'created_at', 'updated_at'}).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(SatisfactionRating, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(self, cursor: str | None, page_size: int = 20) -> CursorPage[SatisfactionRatingEntity]:
        stmt = select(SatisfactionRating).order_by(SatisfactionRating.id).limit(page_size + 1)
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(SatisfactionRating.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [SatisfactionRatingEntity.model_validate(r) for r in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode() if has_next and entities else None
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )


class SqlAlchemyTagRepository(_SqlAlchemyRepository, TagRepository):

    async def add(self, entity: TagEntity) -> None:
        orm = Tag(**entity.model_dump(exclude={'id', 'created_at', 'updated_at'}))
        self._session.add(orm)
        await self._session.flush()

    async def get(self, entity_id: UUID) -> TagEntity | None:
        orm = await self._session.get(Tag, entity_id)
        return TagEntity.model_validate(orm) if orm else None

    async def update(self, entity: TagEntity) -> None:
        orm = await self._session.get(Tag, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(exclude={'id', 'created_at', 'updated_at'}).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(Tag, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(self, cursor: str | None, page_size: int = 20) -> CursorPage[TagEntity]:
        stmt = select(Tag).order_by(Tag.id).limit(page_size + 1)
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(Tag.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [TagEntity.model_validate(r) for r in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode() if has_next and entities else None
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )


class SqlAlchemyTicketTagRepository(_SqlAlchemyRepository, TicketTagRepository):

    async def add(self, entity: TicketTagEntity) -> None:
        orm = TicketTag(**entity.model_dump(exclude={'id', 'created_at', 'updated_at'}))
        self._session.add(orm)
        await self._session.flush()

    async def delete_by_ticket_and_tag(self, ticket_id: UUID, tag_id: UUID) -> None:
        stmt = select(TicketTag).where(
            TicketTag.ticket_id == ticket_id,
            TicketTag.tag_id == tag_id,
        )
        result = await self._session.execute(stmt)
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
        for key, value in entity.model_dump(exclude={'id', 'created_at', 'updated_at'}).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(TicketTag, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(self, cursor: str | None, page_size: int = 20) -> CursorPage[TicketTagEntity]:
        stmt = select(TicketTag).order_by(TicketTag.id).limit(page_size + 1)
        if cursor:
            cursor_id = UUID(base64.urlsafe_b64decode(cursor.encode()).decode())
            stmt = stmt.where(TicketTag.id > cursor_id)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        entities = [TicketTagEntity.model_validate(r) for r in rows[:page_size]]
        has_next = len(rows) > page_size
        next_cursor = base64.urlsafe_b64encode(str(entities[-1].id).encode()).decode() if has_next and entities else None
        return CursorPage(
            items=entities,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )
