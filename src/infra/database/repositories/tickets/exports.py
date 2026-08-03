from __future__ import annotations

from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from src.application.dtos.analytics import (
    AnalyticsFilters,
    ExportTicketRecord,
    SatisfactionExportRecord,
)
from src.infra.database.models import (
    Customer,
    SatisfactionRating,
    Tag,
    Ticket,
    TicketTag,
)
from src.infra.database.repositories.common import enum_value as _enum_value
from src.infra.database.repositories.tickets.base import TicketRepositoryMixinBase


class TicketExportsMixin(TicketRepositoryMixinBase):
    async def count_export_rows(self, filters: AnalyticsFilters) -> int:
        return int(
            (
                await self._session.execute(
                    select(func.count(Ticket.id)).where(
                        *self._ticket_predicates(filters)
                    )
                )
            ).scalar_one()
            or 0
        )

    async def fetch_export_records(
        self,
        filters: AnalyticsFilters,
        limit: int,
        offset: int,
    ) -> list[ExportTicketRecord]:
        rows = (
            await self._session.execute(
                self._export_query(filters).offset(offset).limit(limit)
            )
        ).mappings().all()
        return await self._build_export_records(rows)

    async def iterate_export_records(
        self,
        filters: AnalyticsFilters,
        batch_size: int,
    ) -> AsyncIterator[list[ExportTicketRecord]]:
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero")

        last_external_ticket_id: int | None = None
        while True:
            query = self._export_query(filters)
            if last_external_ticket_id is not None:
                query = query.where(
                    Ticket.external_ticket_id > last_external_ticket_id
                )

            rows = (
                await self._session.execute(query.limit(batch_size))
            ).mappings().all()
            if not rows:
                return

            yield await self._build_export_records(rows)
            if len(rows) < batch_size:
                return
            last_external_ticket_id = int(rows[-1]["external_ticket_id"])

    def _export_query(self, filters: AnalyticsFilters) -> Any:
        return (
            select(
                Ticket.id.label("internal_ticket_id"),
                Ticket.external_ticket_id,
                Ticket.subject,
                Ticket.description,
                Ticket.status,
                Ticket.priority,
                Ticket.assignee_external_id,
                Ticket.assignee_name,
                Ticket.source_created_at,
                Ticket.source_updated_at,
                Ticket.first_response_at,
                Customer.external_requester_id,
                Customer.requester_name,
                Customer.requester_email,
                SatisfactionRating.score.label("satisfaction_score"),
                SatisfactionRating.offered_at,
                SatisfactionRating.rated_at,
                SatisfactionRating.comment,
            )
            .select_from(Ticket)
            .join(Customer, Customer.id == Ticket.customer_id)
            .outerjoin(
                SatisfactionRating,
                SatisfactionRating.ticket_id == Ticket.id,
            )
            .where(*self._ticket_predicates(filters))
            .order_by(Ticket.external_ticket_id.asc())
        )

    async def _build_export_records(
        self,
        rows: Any,
    ) -> list[ExportTicketRecord]:
        ticket_ids = [row["internal_ticket_id"] for row in rows]
        tags_by_ticket: dict[UUID, list[str]] = defaultdict(list)
        if ticket_ids:
            tag_rows = (
                await self._session.execute(
                    select(TicketTag.ticket_id, Tag.name)
                    .join(Tag, Tag.id == TicketTag.tag_id)
                    .where(TicketTag.ticket_id.in_(ticket_ids))
                    .order_by(TicketTag.ticket_id.asc(), Tag.name.asc())
                )
            ).all()
            for ticket_id, tag_name in tag_rows:
                tags_by_ticket[ticket_id].append(tag_name)

        records: list[ExportTicketRecord] = []
        for row in rows:
            rating = None
            if row["satisfaction_score"] is not None:
                rating = SatisfactionExportRecord(
                    score=_enum_value(row["satisfaction_score"]),
                    offered_at=row["offered_at"],
                    rated_at=row["rated_at"],
                    comment=row["comment"] or "",
                )
            records.append(
                ExportTicketRecord(
                    internal_ticket_id=row["internal_ticket_id"],
                    ticket_id=row["external_ticket_id"],
                    subject=row["subject"],
                    description=row["description"],
                    status=_enum_value(row["status"]),
                    priority=_enum_value(row["priority"]),
                    requester_id=row["external_requester_id"],
                    requester_name=row["requester_name"],
                    requester_email=row["requester_email"],
                    assignee_id=row["assignee_external_id"],
                    assignee_name=row["assignee_name"],
                    created_at=row["source_created_at"],
                    updated_at=row["source_updated_at"],
                    first_response_at=row["first_response_at"],
                    tags=tags_by_ticket.get(row["internal_ticket_id"], []),
                    satisfaction_rating=rating,
                )
            )
        return records
