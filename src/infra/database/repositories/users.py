from uuid import UUID

from sqlalchemy import select

from src.application.contracts.repositories import UserRepository
from src.application.dtos.cursor_page import CursorPage
from src.domain.entities import UserEntity
from src.infra.database.models import User
from src.infra.database.repositories.common import (
    SqlAlchemyRepositoryBase,
    decode_uuid_cursor,
    encode_uuid_cursor,
)


class SqlAlchemyUserRepository(SqlAlchemyRepositoryBase, UserRepository):
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
            stmt = stmt.where(User.id > decode_uuid_cursor(cursor))
        rows = list((await self._session.execute(stmt)).scalars().all())
        entities = [UserEntity.model_validate(row) for row in rows[:page_size]]
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
