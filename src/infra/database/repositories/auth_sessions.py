from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult

from src.application.contracts.repositories import AuthSessionRepository
from src.domain.entities import AuthSessionEntity
from src.infra.database.models import AuthSession
from src.infra.database.repositories.common import SqlAlchemyRepositoryBase


class SqlAlchemyAuthSessionRepository(
    SqlAlchemyRepositoryBase,
    AuthSessionRepository,
):
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
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(AuthSession)
                .where(
                    AuthSession.user_id == user_id,
                    AuthSession.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            ),
        )
        await self._session.flush()
        return result.rowcount or 0
