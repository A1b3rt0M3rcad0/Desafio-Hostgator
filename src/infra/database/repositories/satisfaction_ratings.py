from uuid import UUID

from sqlalchemy import select

from src.application.contracts.repositories import SatisfactionRatingRepository
from src.application.dtos.cursor_page import CursorPage
from src.application.dtos.ticket_ingestion import SatisfactionSourceRecord
from src.domain.entities import SatisfactionRatingEntity
from src.infra.database.models import SatisfactionRating
from src.infra.database.repositories.common import (
    SqlAlchemyRepositoryBase,
    decode_uuid_cursor,
    encode_uuid_cursor,
    naive_utc,
)


class SqlAlchemySatisfactionRatingRepository(
    SqlAlchemyRepositoryBase,
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
            stmt = stmt.where(SatisfactionRating.id > decode_uuid_cursor(cursor))
        rows = list((await self._session.execute(stmt)).scalars().all())
        entities = [
            SatisfactionRatingEntity.model_validate(row) for row in rows[:page_size]
        ]
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
            "offered_at": naive_utc(source.offered_at),
            "rated_at": naive_utc(source.rated_at),
            "comment": source.comment,
        }
        if current is None:
            self._session.add(SatisfactionRating(ticket_id=ticket_id, **values))
        else:
            for key, value in values.items():
                setattr(current, key, value)
        await self._session.flush()
