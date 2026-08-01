from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import case, exists, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.contracts.analytics import AnalyticsQueryRepository
from src.application.dtos.analytics import AnalyticsFilters, CustomerMetricsInput
from src.domain.analytics import (
    DataExportField,
    RATED_SATISFACTION_SCORES,
    RESOLVED_STATUSES,
)
from src.infra.database.models import Customer, SatisfactionRating, Tag, Ticket, TicketTag
from src.infra.database.unit_of_work import UnitOfWork


class SqlAlchemyAnalyticsQueryRepository(AnalyticsQueryRepository):
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    @property
    def _session(self) -> AsyncSession:
        return self._unit_of_work.session

    def _ticket_predicates(self, filters: AnalyticsFilters) -> list[Any]:
        predicates: list[Any] = []
        if filters.from_at:
            predicates.append(Ticket.source_created_at >= filters.from_at)
        if filters.to_at:
            predicates.append(Ticket.source_created_at <= filters.to_at)
        if filters.customer_ids:
            predicates.append(Ticket.customer_id.in_(filters.customer_ids))
        if filters.requester_emails:
            predicates.append(
                exists(
                    select(literal_column("1"))
                    .select_from(Customer)
                    .where(
                        Customer.id == Ticket.customer_id,
                        func.lower(Customer.requester_email).in_(filters.requester_emails),
                    )
                )
            )
        if filters.statuses:
            predicates.append(Ticket.status.in_(filters.statuses))
        if filters.priorities:
            predicates.append(Ticket.priority.in_(filters.priorities))
        if filters.assignee_external_ids:
            predicates.append(Ticket.assignee_external_id.in_(filters.assignee_external_ids))
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
            tag_query = tag_query.where(*tag_conditions)
            predicates.append(exists(tag_query))
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
    def _rate(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    @staticmethod
    def _seconds_between(end_column: Any, start_column: Any) -> Any:
        return func.unix_timestamp(end_column) - func.unix_timestamp(start_column)

    async def get_dashboard(
        self,
        filters: AnalyticsFilters,
        top_topics_limit: int,
        timeline_limit: int,
    ) -> dict[str, Any]:
        predicates = self._ticket_predicates(filters)
        total = int(
            (await self._session.execute(select(func.count(Ticket.id)).where(*predicates))).scalar_one()
            or 0
        )

        resolved = int(
            (
                await self._session.execute(
                    select(func.count(Ticket.id)).where(
                        *predicates,
                        Ticket.status.in_(RESOLVED_STATUSES),
                    )
                )
            ).scalar_one()
            or 0
        )

        valid_response = (
            Ticket.first_response_at.is_not(None),
            Ticket.first_response_at >= Ticket.source_created_at,
        )
        response_row = (
            await self._session.execute(
                select(
                    func.avg(
                        self._seconds_between(
                            Ticket.first_response_at,
                            Ticket.source_created_at,
                        )
                    ).label("average_seconds"),
                    func.count(Ticket.id).label("responded_tickets"),
                ).where(*predicates, *valid_response)
            )
        ).mappings().one()
        responded_tickets = int(response_row["responded_tickets"] or 0)
        average_response = response_row["average_seconds"]

        satisfaction_row = (
            await self._session.execute(
                select(
                    func.sum(case((SatisfactionRating.score == "GOOD", 1), else_=0)).label("good"),
                    func.sum(case((SatisfactionRating.score == "BAD", 1), else_=0)).label("bad"),
                )
                .select_from(Ticket)
                .join(SatisfactionRating, SatisfactionRating.ticket_id == Ticket.id)
                .where(
                    *predicates,
                    SatisfactionRating.score.in_(RATED_SATISFACTION_SCORES),
                )
            )
        ).mappings().one()
        good = int(satisfaction_row["good"] or 0)
        bad = int(satisfaction_row["bad"] or 0)
        rated_total = good + bad

        ordered_tickets = (
            select(
                Ticket.customer_id.label("customer_id"),
                Ticket.source_created_at.label("current_at"),
                func.lag(Ticket.source_created_at)
                .over(
                    partition_by=Ticket.customer_id,
                    order_by=(Ticket.source_created_at, Ticket.id),
                )
                .label("previous_at"),
            )
            .where(*predicates)
            .subquery()
        )
        recurrence_row = (
            await self._session.execute(
                select(
                    func.avg(
                        self._seconds_between(
                            ordered_tickets.c.current_at,
                            ordered_tickets.c.previous_at,
                        )
                    ).label("average_seconds"),
                    func.count(ordered_tickets.c.previous_at).label("sample_intervals"),
                    func.count(func.distinct(ordered_tickets.c.customer_id)).label("customers"),
                ).where(ordered_tickets.c.previous_at.is_not(None))
            )
        ).mappings().one()

        top_topics_rows = (
            await self._session.execute(
                select(
                    Tag.name.label("tag"),
                    func.count(func.distinct(Ticket.id)).label("ticket_count"),
                )
                .select_from(Ticket)
                .join(TicketTag, TicketTag.ticket_id == Ticket.id)
                .join(Tag, Tag.id == TicketTag.tag_id)
                .where(*predicates)
                .group_by(Tag.id, Tag.name)
                .order_by(func.count(func.distinct(Ticket.id)).desc(), Tag.name.asc())
                .limit(top_topics_limit)
            )
        ).mappings().all()

        status_rows = (
            await self._session.execute(
                select(Ticket.status.label("label"), func.count(Ticket.id).label("value"))
                .where(*predicates)
                .group_by(Ticket.status)
                .order_by(func.count(Ticket.id).desc())
            )
        ).mappings().all()
        priority_rows = (
            await self._session.execute(
                select(Ticket.priority.label("label"), func.count(Ticket.id).label("value"))
                .where(*predicates)
                .group_by(Ticket.priority)
                .order_by(func.count(Ticket.id).desc())
            )
        ).mappings().all()
        timeline_rows = list(
            reversed(
                (
                    await self._session.execute(
                        select(
                            func.date(Ticket.source_created_at).label("date"),
                            func.count(Ticket.id).label("value"),
                        )
                        .where(*predicates)
                        .group_by(func.date(Ticket.source_created_at))
                        .order_by(func.date(Ticket.source_created_at).desc())
                        .limit(timeline_limit)
                    )
                ).mappings().all()
            )
        )

        top_topics = []
        for rank, row in enumerate(top_topics_rows, start=1):
            count = int(row["ticket_count"] or 0)
            top_topics.append(
                {
                    "tag": row["tag"],
                    "ticket_count": count,
                    "share": self._rate(count, total),
                    "rank": rank,
                }
            )

        return {
            "filters": filters.model_dump(mode="json"),
            "metrics": {
                "ticket_volume": {"value": total},
                "average_recurrence": {
                    "average_seconds": round(float(recurrence_row["average_seconds"]), 2)
                    if recurrence_row["average_seconds"] is not None
                    else None,
                    "sample_intervals": int(recurrence_row["sample_intervals"] or 0),
                    "customers_with_recurrence": int(recurrence_row["customers"] or 0),
                },
                "resolution_rate": {
                    "rate": self._rate(resolved, total),
                    "resolved": resolved,
                    "total": total,
                },
                "satisfaction_rate": {
                    "rate": self._rate(good, rated_total),
                    "good": good,
                    "bad": bad,
                    "rated_total": rated_total,
                },
                "average_first_response": {
                    "average_seconds": round(float(average_response), 2)
                    if average_response is not None
                    else None,
                    "responded_tickets": responded_tickets,
                    "unanswered_tickets": max(total - responded_tickets, 0),
                },
            },
            "charts": {
                "tickets_over_time": [
                    {"date": str(row["date"]), "value": int(row["value"] or 0)}
                    for row in timeline_rows
                ],
                "status_distribution": [
                    {"label": self._enum_value(row["label"]), "value": int(row["value"] or 0)}
                    for row in status_rows
                ],
                "priority_distribution": [
                    {"label": self._enum_value(row["label"]), "value": int(row["value"] or 0)}
                    for row in priority_rows
                ],
                "top_topics": top_topics,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def list_customer_metrics(
        self,
        input_dto: CustomerMetricsInput,
    ) -> dict[str, Any]:
        predicates = self._ticket_predicates(input_dto)
        customer_ids_subquery = (
            select(Ticket.customer_id.label("customer_id"))
            .where(*predicates)
            .group_by(Ticket.customer_id)
            .subquery()
        )
        total_customers = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(customer_ids_subquery)
                )
            ).scalar_one()
            or 0
        )
        offset = (input_dto.page - 1) * input_dto.page_size
        base_rows = (
            await self._session.execute(
                select(
                    Customer.id.label("customer_id"),
                    Customer.external_requester_id,
                    Customer.requester_name,
                    Customer.requester_email,
                    func.count(Ticket.id).label("ticket_volume"),
                    func.sum(case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)).label("resolved"),
                    func.avg(
                        case(
                            (
                                Ticket.first_response_at.is_not(None)
                                & (Ticket.first_response_at >= Ticket.source_created_at),
                                self._seconds_between(
                                    Ticket.first_response_at,
                                    Ticket.source_created_at,
                                ),
                            ),
                            else_=None,
                        )
                    ).label("average_first_response_seconds"),
                )
                .select_from(Ticket)
                .join(Customer, Customer.id == Ticket.customer_id)
                .where(*predicates)
                .group_by(
                    Customer.id,
                    Customer.external_requester_id,
                    Customer.requester_name,
                    Customer.requester_email,
                )
                .order_by(func.count(Ticket.id).desc(), Customer.requester_name.asc())
                .offset(offset)
                .limit(input_dto.page_size)
            )
        ).mappings().all()
        page_customer_ids = [row["customer_id"] for row in base_rows]
        if not page_customer_ids:
            return {
                "items": [],
                "page": input_dto.page,
                "page_size": input_dto.page_size,
                "total": total_customers,
                "has_next": False,
                "has_previous": input_dto.page > 1,
            }

        satisfaction_rows = (
            await self._session.execute(
                select(
                    Ticket.customer_id,
                    func.sum(case((SatisfactionRating.score == "GOOD", 1), else_=0)).label("good"),
                    func.sum(case((SatisfactionRating.score == "BAD", 1), else_=0)).label("bad"),
                )
                .select_from(Ticket)
                .join(SatisfactionRating, SatisfactionRating.ticket_id == Ticket.id)
                .where(
                    *predicates,
                    Ticket.customer_id.in_(page_customer_ids),
                    SatisfactionRating.score.in_(RATED_SATISFACTION_SCORES),
                )
                .group_by(Ticket.customer_id)
            )
        ).mappings().all()
        satisfaction_by_customer = {row["customer_id"]: row for row in satisfaction_rows}

        ordered = (
            select(
                Ticket.customer_id.label("customer_id"),
                Ticket.source_created_at.label("current_at"),
                func.lag(Ticket.source_created_at)
                .over(
                    partition_by=Ticket.customer_id,
                    order_by=(Ticket.source_created_at, Ticket.id),
                )
                .label("previous_at"),
            )
            .where(*predicates, Ticket.customer_id.in_(page_customer_ids))
            .subquery()
        )
        recurrence_rows = (
            await self._session.execute(
                select(
                    ordered.c.customer_id,
                    func.avg(
                        self._seconds_between(
                            ordered.c.current_at,
                            ordered.c.previous_at,
                        )
                    ).label("average_seconds"),
                    func.count(ordered.c.previous_at).label("sample_intervals"),
                )
                .where(ordered.c.previous_at.is_not(None))
                .group_by(ordered.c.customer_id)
            )
        ).mappings().all()
        recurrence_by_customer = {row["customer_id"]: row for row in recurrence_rows}

        topic_rows = (
            await self._session.execute(
                select(
                    Ticket.customer_id,
                    Tag.name.label("tag"),
                    func.count(func.distinct(Ticket.id)).label("ticket_count"),
                )
                .select_from(Ticket)
                .join(TicketTag, TicketTag.ticket_id == Ticket.id)
                .join(Tag, Tag.id == TicketTag.tag_id)
                .where(*predicates, Ticket.customer_id.in_(page_customer_ids))
                .group_by(Ticket.customer_id, Tag.id, Tag.name)
                .order_by(
                    Ticket.customer_id.asc(),
                    func.count(func.distinct(Ticket.id)).desc(),
                    Tag.name.asc(),
                )
            )
        ).mappings().all()
        topics_by_customer: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
        for row in topic_rows:
            bucket = topics_by_customer[row["customer_id"]]
            if len(bucket) < input_dto.top_topics_limit:
                bucket.append(
                    {"tag": row["tag"], "ticket_count": int(row["ticket_count"] or 0)}
                )

        items: list[dict[str, Any]] = []
        for row in base_rows:
            customer_id = row["customer_id"]
            volume = int(row["ticket_volume"] or 0)
            resolved = int(row["resolved"] or 0)
            satisfaction = satisfaction_by_customer.get(customer_id, {})
            good = int(satisfaction.get("good") or 0)
            bad = int(satisfaction.get("bad") or 0)
            recurrence = recurrence_by_customer.get(customer_id, {})
            response_average = row["average_first_response_seconds"]
            items.append(
                {
                    "customer_id": str(customer_id),
                    "external_requester_id": row["external_requester_id"],
                    "requester_name": row["requester_name"],
                    "requester_email": row["requester_email"],
                    "ticket_volume": volume,
                    "average_recurrence_seconds": round(float(recurrence["average_seconds"]), 2)
                    if recurrence.get("average_seconds") is not None
                    else None,
                    "recurrence_sample_intervals": int(recurrence.get("sample_intervals") or 0),
                    "resolution_rate": self._rate(resolved, volume),
                    "resolved_tickets": resolved,
                    "satisfaction_rate": self._rate(good, good + bad),
                    "good_ratings": good,
                    "bad_ratings": bad,
                    "average_first_response_seconds": round(float(response_average), 2)
                    if response_average is not None
                    else None,
                    "top_topics": topics_by_customer.get(customer_id, []),
                }
            )

        return {
            "items": items,
            "page": input_dto.page,
            "page_size": input_dto.page_size,
            "total": total_customers,
            "has_next": offset + len(items) < total_customers,
            "has_previous": input_dto.page > 1,
        }

    async def count_export_rows(self, filters: AnalyticsFilters) -> int:
        return int(
            (
                await self._session.execute(
                    select(func.count(Ticket.id)).where(*self._ticket_predicates(filters))
                )
            ).scalar_one()
            or 0
        )

    async def fetch_export_rows(
        self,
        filters: AnalyticsFilters,
        fields: list[DataExportField],
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        predicates = self._ticket_predicates(filters)
        rows = (
            await self._session.execute(
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
                .outerjoin(SatisfactionRating, SatisfactionRating.ticket_id == Ticket.id)
                .where(*predicates)
                .order_by(Ticket.external_ticket_id.asc())
                .offset(offset)
                .limit(limit)
            )
        ).mappings().all()
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

        requested_fields = [field.value for field in fields]
        output: list[dict[str, Any]] = []
        for row in rows:
            rating = None
            if row["satisfaction_score"] is not None:
                rating = {
                    "score": self._enum_value(row["satisfaction_score"]).lower(),
                    "offered_at": self._iso(row["offered_at"]),
                    "rated_at": self._iso(row["rated_at"]),
                    "comment": row["comment"] or "",
                }
            complete = {
                "ticket_id": row["external_ticket_id"],
                "subject": row["subject"],
                "description": row["description"],
                "status": self._enum_value(row["status"]).lower(),
                "priority": self._enum_value(row["priority"]).lower(),
                "requester_id": row["external_requester_id"],
                "requester_name": row["requester_name"],
                "requester_email": row["requester_email"],
                "assignee_id": row["assignee_external_id"],
                "assignee_name": row["assignee_name"],
                "created_at": self._iso(row["source_created_at"]),
                "updated_at": self._iso(row["source_updated_at"]),
                "first_response_at": self._iso(row["first_response_at"]),
                "tags": tags_by_ticket.get(row["internal_ticket_id"], []),
                "satisfaction_rating": rating,
            }
            output.append({field: complete[field] for field in requested_fields})
        return output

    @staticmethod
    def _enum_value(value: Any) -> str:
        return str(value.value if isinstance(value, Enum) else value)

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
