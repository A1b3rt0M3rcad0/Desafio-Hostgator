from __future__ import annotations

import base64
from uuid import UUID

from sqlalchemy import select

from src.application.contracts.repositories import TicketRepository
from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import TicketEntity
from src.infra.database.models import Ticket
from src.infra.database.repositories.tickets.analytics import TicketAnalyticsMixin
from src.infra.database.repositories.tickets.base import TicketRepositoryMixinBase
from src.infra.database.repositories.tickets.exports import TicketExportsMixin
from src.infra.database.repositories.tickets.ingestion import TicketIngestionMixin
from src.infra.database.repositories.tickets.listings import TicketListingsMixin


class TicketCrudMixin(TicketRepositoryMixinBase):
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


class SqlAlchemyTicketRepository(
    TicketCrudMixin,
    TicketIngestionMixin,
    TicketListingsMixin,
    TicketAnalyticsMixin,
    TicketExportsMixin,
    TicketRepository,
):
    pass
