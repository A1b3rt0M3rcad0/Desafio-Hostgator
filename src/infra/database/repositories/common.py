from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, overload
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.database.unit_of_work import UnitOfWork


class SqlAlchemyRepositoryBase:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    @property
    def _session(self) -> AsyncSession:
        return self._unit_of_work.session


@overload
def naive_utc(value: datetime) -> datetime: ...


@overload
def naive_utc(value: None) -> None: ...


def naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def enum_value(value: Any) -> str:
    return str(value.value if isinstance(value, Enum) else value)


def encode_json_cursor(payload: dict[str, str]) -> str:
    serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return base64.urlsafe_b64encode(serialized.encode()).decode()


def decode_json_cursor(cursor: str) -> dict[str, str]:
    decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
    payload = json.loads(decoded)
    if not isinstance(payload, dict):
        raise ValueError("Invalid cursor")
    return {str(key): str(value) for key, value in payload.items()}


def encode_uuid_cursor(entity_id: UUID) -> str:
    return base64.urlsafe_b64encode(str(entity_id).encode()).decode()


def decode_uuid_cursor(cursor: str) -> UUID:
    return UUID(base64.urlsafe_b64decode(cursor.encode()).decode())


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
