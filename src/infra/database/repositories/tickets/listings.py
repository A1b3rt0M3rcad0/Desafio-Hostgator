from __future__ import annotations

import base64
import re
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, exists, func, literal_column, or_, select
from sqlalchemy.dialects.mysql import match as mysql_match

from src.application.dtos.analytics import AnalyticsFilters
from src.application.dtos.cursor_page import CursorPage
from src.application.dtos.list_tickets import ListTicketsInput, TicketListItem
from src.domain.entities import TicketEntity
from src.infra.database.models import Customer, SatisfactionRating, Tag, Ticket, TicketTag
from src.infra.database.repositories.common import (
    decode_json_cursor as _decode_json_cursor,
    encode_json_cursor as _encode_json_cursor,
    escape_like as _escape_like,
    naive_utc as _naive_utc,
)
from src.infra.database.repositories.tickets.base import TicketRepositoryMixinBase


class TicketListingsMixin(TicketRepositoryMixinBase):
    async def page_list(
        self,
        input_dto: ListTicketsInput,
    ) -> CursorPage[TicketListItem]:
        predicates: list[Any] = []
        if input_dto.statuses:
            predicates.append(Ticket.status.in_(input_dto.statuses))
        if input_dto.priorities:
            predicates.append(Ticket.priority.in_(input_dto.priorities))
        if input_dto.from_at is not None:
            predicates.append(Ticket.source_created_at >= _naive_utc(input_dto.from_at))
        if input_dto.to_at is not None:
            predicates.append(Ticket.source_created_at <= _naive_utc(input_dto.to_at))
        if input_dto.search:
            search = input_dto.search
            search_conditions: list[Any] = []
            if search.isdigit():
                search_conditions.append(Ticket.external_ticket_id == int(search))
            boolean_query = self._boolean_search_query(search)
            if boolean_query:
                search_conditions.append(
                    mysql_match(
                        cast(Any, Ticket.subject),
                        cast(Any, Ticket.description),
                        against=boolean_query,
                    ).in_boolean_mode()
                )
            escaped = _escape_like(search)
            search_conditions.append(
                Ticket.assignee_name.like(f"{escaped}%", escape="\\")
            )
            predicates.append(or_(*search_conditions))

        if input_dto.cursor:
            payload = _decode_json_cursor(input_dto.cursor)
            cursor_at = payload.get("source_created_at")
            cursor_id = payload.get("id")
            if cursor_at is None or cursor_id is None:
                raise ValueError("Invalid ticket cursor")
            parsed_at = datetime.fromisoformat(cursor_at)
            parsed_id = UUID(cursor_id)
            predicates.append(
                or_(
                    Ticket.source_created_at < parsed_at,
                    and_(
                        Ticket.source_created_at == parsed_at,
                        Ticket.id < parsed_id,
                    ),
                )
            )

        rows = (
            await self._session.execute(
                select(
                    Ticket.id,
                    Ticket.external_ticket_id,
                    Ticket.subject,
                    Ticket.status,
                    Ticket.priority,
                    Ticket.assignee_name,
                    Ticket.source_created_at,
                    Ticket.source_updated_at,
                )
                .where(*predicates)
                .order_by(Ticket.source_created_at.desc(), Ticket.id.desc())
                .limit(input_dto.page_size + 1)
            )
        ).mappings().all()
        items = [
            TicketListItem(
                id=row["id"],
                external_ticket_id=row["external_ticket_id"],
                subject=row["subject"],
                status=row["status"],
                priority=row["priority"],
                assignee_name=row["assignee_name"],
                source_created_at=row["source_created_at"],
                source_updated_at=row["source_updated_at"],
            )
            for row in rows[: input_dto.page_size]
        ]
        has_next = len(rows) > input_dto.page_size
        next_cursor = (
            _encode_json_cursor(
                {
                    "source_created_at": items[-1].source_created_at.isoformat(),
                    "id": str(items[-1].id),
                }
            )
            if has_next and items
            else None
        )
        return CursorPage(
            items=items,
            next_cursor=next_cursor,
            previous_cursor=None,
            has_next=has_next,
            has_previous=input_dto.cursor is not None,
        )

    async def page_by_tag_ids(
        self,
        tag_ids: list[UUID],
        cursor: str | None = None,
        page_size: int = 20,
    ) -> CursorPage[TicketEntity]:
        stmt = (
            select(Ticket)
            .join(TicketTag, Ticket.id == TicketTag.ticket_id)
            .where(TicketTag.tag_id.in_(tag_ids))
            .distinct()
            .order_by(Ticket.id)
            .limit(page_size + 1)
        )
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

    def _ticket_predicates(self, filters: AnalyticsFilters) -> list[Any]:
        predicates: list[Any] = []
        if filters.from_at is not None:
            predicates.append(
                Ticket.source_created_at >= _naive_utc(filters.from_at)
            )
        if filters.to_at is not None:
            predicates.append(
                Ticket.source_created_at <= _naive_utc(filters.to_at)
            )
        if filters.customer_ids:
            predicates.append(Ticket.customer_id.in_(filters.customer_ids))
        if filters.requester_emails:
            predicates.append(
                exists(
                    select(literal_column("1"))
                    .select_from(Customer)
                    .where(
                        Customer.id == Ticket.customer_id,
                        func.lower(Customer.requester_email).in_(
                            filters.requester_emails
                        ),
                    )
                )
            )
        if filters.statuses:
            predicates.append(Ticket.status.in_(filters.statuses))
        if filters.priorities:
            predicates.append(Ticket.priority.in_(filters.priorities))
        if filters.assignee_external_ids:
            predicates.append(
                Ticket.assignee_external_id.in_(filters.assignee_external_ids)
            )
        if filters.tag_ids or filters.tag_names:
            tag_query = (
                select(literal_column("1"))
                .select_from(TicketTag)
                .join(Tag, Tag.id == TicketTag.tag_id)
                .where(TicketTag.ticket_id == Ticket.id)
            )
            tag_conditions: list[Any] = []
            if filters.tag_ids:
                tag_conditions.append(Tag.id.in_(filters.tag_ids))
            if filters.tag_names:
                tag_conditions.append(Tag.name.in_(filters.tag_names))
            predicates.append(exists(tag_query.where(*tag_conditions)))
        if filters.satisfaction_scores:
            predicates.append(
                exists(
                    select(literal_column("1"))
                    .select_from(SatisfactionRating)
                    .where(
                        SatisfactionRating.ticket_id == Ticket.id,
                        SatisfactionRating.score.in_(filters.satisfaction_scores),
                    )
                )
            )
        if filters.has_first_response is True:
            predicates.append(Ticket.first_response_at.is_not(None))
        elif filters.has_first_response is False:
            predicates.append(Ticket.first_response_at.is_(None))
        return predicates

    @staticmethod
    def _boolean_search_query(value: str) -> str | None:
        tokens = re.findall(r"[\wÀ-ÿ]+", value, flags=re.UNICODE)
        if not tokens:
            return None
        return " ".join(f"+{token}*" for token in tokens[:10])
