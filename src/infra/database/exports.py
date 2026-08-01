from __future__ import annotations

from typing import Any

from sqlalchemy import select

from src.application.contracts.exports import DataExportRepository
from src.application.dtos.analytics import AnalyticsFilters
from src.domain.analytics import DataExportField
from src.infra.database.analytics import SqlAlchemyAnalyticsQueryRepository
from src.infra.database.models import Customer, Tag, Ticket
from src.infra.database.unit_of_work import UnitOfWork


class SqlAlchemyDataExportRepository(
    SqlAlchemyAnalyticsQueryRepository,
    DataExportRepository,
):
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        super().__init__(unit_of_work)

    async def count_rows(self, filters: AnalyticsFilters) -> int:
        return await self.count_export_rows(filters)

    async def fetch_rows(
        self,
        filters: AnalyticsFilters,
        fields: list[DataExportField],
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        return await self.fetch_export_rows(filters, fields, limit, offset)

    async def get_filter_options(self) -> dict[str, list[dict[str, Any]]]:
        tags = (
            await self._session.execute(
                select(Tag.id, Tag.name).order_by(Tag.name.asc())
            )
        ).all()
        customers = (
            await self._session.execute(
                select(
                    Customer.id,
                    Customer.requester_name,
                    Customer.requester_email,
                ).order_by(Customer.requester_name.asc(), Customer.requester_email.asc())
            )
        ).all()
        assignees = (
            await self._session.execute(
                select(Ticket.assignee_external_id, Ticket.assignee_name)
                .where(Ticket.assignee_external_id.is_not(None))
                .group_by(Ticket.assignee_external_id, Ticket.assignee_name)
                .order_by(Ticket.assignee_name.asc())
            )
        ).all()
        return {
            "tags": [
                {"id": str(tag_id), "name": name}
                for tag_id, name in tags
            ],
            "customers": [
                {
                    "id": str(customer_id),
                    "requester_name": requester_name,
                    "requester_email": requester_email,
                }
                for customer_id, requester_name, requester_email in customers
            ],
            "assignees": [
                {
                    "external_id": external_id,
                    "name": name or f"Responsável {external_id}",
                }
                for external_id, name in assignees
            ],
        }
