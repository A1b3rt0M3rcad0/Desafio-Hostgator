from __future__ import annotations

from typing import Any

from sqlalchemy import select

from src.application.dtos.analytics import AnalyticsFilters
from src.infra.database.dashboard_analytics import DashboardAnalyticsQueryRepository
from src.infra.database.models import Customer, Tag, Ticket


class DashboardWorkspaceQueryRepository(DashboardAnalyticsQueryRepository):
    """Agrega métricas, séries e dimensões de filtro em uma única leitura autenticada."""

    async def get_dashboard(
        self,
        filters: AnalyticsFilters,
        top_topics_limit: int,
        timeline_limit: int,
    ) -> dict[str, Any]:
        dashboard = await super().get_dashboard(filters, top_topics_limit, timeline_limit)
        dashboard["filter_options"] = await self._get_filter_options()
        return dashboard

    async def _get_filter_options(self) -> dict[str, list[dict[str, Any]]]:
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
                select(
                    Ticket.assignee_external_id,
                    Ticket.assignee_name,
                )
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
