from uuid import UUID

from sqlalchemy import select

from src.application.contracts.repositories import TagRepository
from src.application.dtos.analytics import TagFilterOption
from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import TagEntity
from src.infra.database.models import Tag
from src.infra.database.repositories.common import (
    SqlAlchemyRepositoryBase,
    decode_uuid_cursor,
    encode_uuid_cursor,
)


class SqlAlchemyTagRepository(SqlAlchemyRepositoryBase, TagRepository):
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
            stmt = stmt.where(Tag.id > decode_uuid_cursor(cursor))
        rows = list((await self._session.execute(stmt)).scalars().all())
        entities = [TagEntity.model_validate(row) for row in rows[:page_size]]
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
