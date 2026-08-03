from __future__ import annotations

from typing import Any

from src.application.dtos.analytics import AnalyticsFilters
from src.infra.database.repositories.common import SqlAlchemyRepositoryBase


class TicketRepositoryMixinBase(SqlAlchemyRepositoryBase):
    def _ticket_predicates(self, filters: AnalyticsFilters) -> list[Any]:
        raise NotImplementedError

    @staticmethod
    def _seconds_between(end_column: Any, start_column: Any) -> Any:
        raise NotImplementedError

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        raise NotImplementedError
