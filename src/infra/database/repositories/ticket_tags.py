from uuid import UUID

from sqlalchemy import delete, select

from src.application.contracts.repositories import TicketTagRepository
from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import TicketTagEntity
from src.infra.database.models import TicketTag
from src.infra.database.repositories.common import (
    SqlAlchemyRepositoryBase,
    decode_uuid_cursor,
    encode_uuid_cursor,
)


class SqlAlchemyTicketTagRepository(
    SqlAlchemyRepositoryBase,
    TicketTagRepository,
):
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
            stmt = stmt.where(TicketTag.id > decode_uuid_cursor(cursor))
        rows = list((await self._session.execute(stmt)).scalars().all())
        entities = [TicketTagEntity.model_validate(row) for row in rows[:page_size]]
        has_next = len(rows) > page_size
        return CursorPage(
            items=entities,
            next_cursor=(
                encode_uuid_cursor(entities[-1].id)
                if has_next and entities and entities[-1].id is not None
                else None
            ),
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
