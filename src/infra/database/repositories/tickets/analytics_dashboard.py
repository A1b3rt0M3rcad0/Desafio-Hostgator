from __future__ import annotations

from typing import Any

from sqlalchemy import and_, case, func, or_, select

from src.application.dtos.analytics import (
    AnalyticsFilters,
    DashboardOperationalSnapshot,
    DashboardPeriodSnapshot,
    PriorityAggregate,
    ResponseBucketAggregate,
    StatusAggregate,
    TimelineAggregate,
    TopCustomerAggregate,
    TopicAggregate,
)
from src.domain.analytics import RESOLVED_STATUSES
from src.infra.database.models import (
    Customer,
    SatisfactionRating,
    Tag,
    Ticket,
    TicketTag,
)
from src.infra.database.repositories.common import enum_value as _enum_value
from src.infra.database.repositories.tickets.base import TicketRepositoryMixinBase


class TicketDashboardAnalyticsMixin(TicketRepositoryMixinBase):
    async def get_dashboard_period_snapshot(
        self,
        filters: AnalyticsFilters,
        top_topics_limit: int,
    ) -> DashboardPeriodSnapshot:
        predicates = self._ticket_predicates(filters)
        valid_response = and_(
            Ticket.first_response_at.is_not(None),
            Ticket.first_response_at >= Ticket.source_created_at,
        )
        valid_response_seconds = case(
            (
                valid_response,
                self._seconds_between(
                    Ticket.first_response_at,
                    Ticket.source_created_at,
                ),
            ),
            else_=None,
        )
        summary = (
            await self._session.execute(
                select(
                    func.count(Ticket.id).label("total_tickets"),
                    func.sum(
                        case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)
                    ).label("resolved_tickets"),
                    func.avg(valid_response_seconds).label(
                        "average_first_response_seconds"
                    ),
                    func.sum(case((valid_response, 1), else_=0)).label(
                        "responded_tickets"
                    ),
                    func.sum(
                        case((SatisfactionRating.score == "GOOD", 1), else_=0)
                    ).label("good_ratings"),
                    func.sum(
                        case((SatisfactionRating.score == "BAD", 1), else_=0)
                    ).label("bad_ratings"),
                )
                .select_from(Ticket)
                .outerjoin(
                    SatisfactionRating,
                    SatisfactionRating.ticket_id == Ticket.id,
                )
                .where(*predicates)
            )
        ).mappings().one()

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
        recurrence = (
            await self._session.execute(
                select(
                    func.avg(
                        self._seconds_between(
                            ordered_tickets.c.current_at,
                            ordered_tickets.c.previous_at,
                        )
                    ).label("average_seconds"),
                    func.count(ordered_tickets.c.previous_at).label(
                        "sample_intervals"
                    ),
                    func.count(
                        func.distinct(ordered_tickets.c.customer_id)
                    ).label("customers"),
                ).where(ordered_tickets.c.previous_at.is_not(None))
            )
        ).mappings().one()

        status_rows = (
            await self._session.execute(
                select(
                    Ticket.status.label("label"),
                    func.count(Ticket.id).label("value"),
                )
                .where(*predicates)
                .group_by(Ticket.status)
                .order_by(func.count(Ticket.id).desc())
            )
        ).mappings().all()

        priority_rows = (
            await self._session.execute(
                select(
                    Ticket.priority.label("priority"),
                    func.count(Ticket.id).label("ticket_count"),
                    func.sum(
                        case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)
                    ).label("resolved_tickets"),
                    func.avg(valid_response_seconds).label(
                        "average_first_response_seconds"
                    ),
                )
                .where(*predicates)
                .group_by(Ticket.priority)
                .order_by(func.count(Ticket.id).desc())
            )
        ).mappings().all()

        topic_rows = (
            await self._session.execute(
                select(
                    Tag.name.label("tag"),
                    func.count(func.distinct(Ticket.id)).label("ticket_count"),
                    func.sum(
                        case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)
                    ).label("resolved_tickets"),
                    func.avg(valid_response_seconds).label(
                        "average_first_response_seconds"
                    ),
                )
                .select_from(Ticket)
                .join(TicketTag, TicketTag.ticket_id == Ticket.id)
                .join(Tag, Tag.id == TicketTag.tag_id)
                .where(*predicates)
                .group_by(Tag.id, Tag.name)
                .order_by(
                    func.count(func.distinct(Ticket.id)).desc(),
                    Tag.name.asc(),
                )
                .limit(top_topics_limit)
            )
        ).mappings().all()

        return DashboardPeriodSnapshot(
            total_tickets=int(summary["total_tickets"] or 0),
            resolved_tickets=int(summary["resolved_tickets"] or 0),
            average_first_response_seconds=self._optional_float(
                summary["average_first_response_seconds"]
            ),
            responded_tickets=int(summary["responded_tickets"] or 0),
            good_ratings=int(summary["good_ratings"] or 0),
            bad_ratings=int(summary["bad_ratings"] or 0),
            average_recurrence_seconds=self._optional_float(
                recurrence["average_seconds"]
            ),
            recurrence_sample_intervals=int(recurrence["sample_intervals"] or 0),
            customers_with_recurrence=int(recurrence["customers"] or 0),
            status_counts=[
                StatusAggregate(
                    label=_enum_value(row["label"]),
                    value=int(row["value"] or 0),
                )
                for row in status_rows
            ],
            priority_aggregates=[
                PriorityAggregate(
                    priority=_enum_value(row["priority"]),
                    ticket_count=int(row["ticket_count"] or 0),
                    resolved_tickets=int(row["resolved_tickets"] or 0),
                    average_first_response_seconds=self._optional_float(
                        row["average_first_response_seconds"]
                    ),
                )
                for row in priority_rows
            ],
            topic_aggregates=[
                TopicAggregate(
                    tag=row["tag"],
                    ticket_count=int(row["ticket_count"] or 0),
                    resolved_tickets=int(row["resolved_tickets"] or 0),
                    average_first_response_seconds=self._optional_float(
                        row["average_first_response_seconds"]
                    ),
                )
                for row in topic_rows
            ],
        )

    async def get_dashboard_operational_snapshot(
        self,
        filters: AnalyticsFilters,
        timeline_limit: int,
    ) -> DashboardOperationalSnapshot:
        predicates = self._ticket_predicates(filters)
        valid_response = and_(
            Ticket.first_response_at.is_not(None),
            Ticket.first_response_at >= Ticket.source_created_at,
        )
        valid_response_seconds = case(
            (
                valid_response,
                self._seconds_between(
                    Ticket.first_response_at,
                    Ticket.source_created_at,
                ),
            ),
            else_=None,
        )

        timeline_rows = list(
            reversed(
                (
                    await self._session.execute(
                        select(
                            func.date(Ticket.source_created_at).label("date"),
                            func.count(Ticket.id).label("opened"),
                            func.sum(
                                case(
                                    (Ticket.status.in_(RESOLVED_STATUSES), 1),
                                    else_=0,
                                )
                            ).label("resolved"),
                            func.avg(valid_response_seconds).label(
                                "average_first_response_seconds"
                            ),
                            func.sum(
                                case(
                                    (SatisfactionRating.score == "GOOD", 1),
                                    else_=0,
                                )
                            ).label("good_ratings"),
                            func.sum(
                                case(
                                    (SatisfactionRating.score == "BAD", 1),
                                    else_=0,
                                )
                            ).label("bad_ratings"),
                        )
                        .select_from(Ticket)
                        .outerjoin(
                            SatisfactionRating,
                            SatisfactionRating.ticket_id == Ticket.id,
                        )
                        .where(*predicates)
                        .group_by(func.date(Ticket.source_created_at))
                        .order_by(func.date(Ticket.source_created_at).desc())
                        .limit(timeline_limit)
                    )
                ).mappings().all()
            )
        )

        response_seconds = self._seconds_between(
            Ticket.first_response_at,
            Ticket.source_created_at,
        )
        response_bucket = case(
            (
                or_(
                    Ticket.first_response_at.is_(None),
                    Ticket.first_response_at < Ticket.source_created_at,
                ),
                "unanswered",
            ),
            (response_seconds <= 15 * 60, "up_to_15m"),
            (response_seconds <= 30 * 60, "15_to_30m"),
            (response_seconds <= 60 * 60, "30_to_60m"),
            (response_seconds <= 4 * 60 * 60, "1_to_4h"),
            else_="over_4h",
        ).label("bucket")
        response_rows = (
            await self._session.execute(
                select(response_bucket, func.count(Ticket.id).label("ticket_count"))
                .where(*predicates)
                .group_by(response_bucket)
            )
        ).mappings().all()

        per_customer = (
            select(
                Ticket.customer_id.label("customer_id"),
                func.count(Ticket.id).label("ticket_count"),
            )
            .where(*predicates)
            .group_by(Ticket.customer_id)
            .subquery()
        )
        behavior = (
            await self._session.execute(
                select(
                    func.count(per_customer.c.customer_id).label("unique_customers"),
                    func.sum(
                        case((per_customer.c.ticket_count > 1, 1), else_=0)
                    ).label("repeat_customers"),
                    func.avg(per_customer.c.ticket_count).label(
                        "average_tickets_per_customer"
                    ),
                )
            )
        ).mappings().one()

        top_customer_rows = (
            await self._session.execute(
                select(
                    Customer.id.label("customer_id"),
                    Customer.requester_name,
                    Customer.requester_email,
                    func.count(Ticket.id).label("ticket_count"),
                )
                .select_from(Ticket)
                .join(Customer, Customer.id == Ticket.customer_id)
                .where(*predicates)
                .group_by(
                    Customer.id,
                    Customer.requester_name,
                    Customer.requester_email,
                )
                .order_by(func.count(Ticket.id).desc(), Customer.requester_name.asc())
                .limit(5)
            )
        ).mappings().all()

        return DashboardOperationalSnapshot(
            timeline=[
                TimelineAggregate(
                    date=str(row["date"]),
                    opened=int(row["opened"] or 0),
                    resolved=int(row["resolved"] or 0),
                    average_first_response_seconds=self._optional_float(
                        row["average_first_response_seconds"]
                    ),
                    good_ratings=int(row["good_ratings"] or 0),
                    bad_ratings=int(row["bad_ratings"] or 0),
                )
                for row in timeline_rows
            ],
            response_buckets=[
                ResponseBucketAggregate(
                    bucket=row["bucket"],
                    ticket_count=int(row["ticket_count"] or 0),
                )
                for row in response_rows
            ],
            unique_customers=int(behavior["unique_customers"] or 0),
            repeat_customers=int(behavior["repeat_customers"] or 0),
            average_tickets_per_customer=self._optional_float(
                behavior["average_tickets_per_customer"]
            ),
            top_customers=[
                TopCustomerAggregate(
                    customer_id=row["customer_id"],
                    requester_name=row["requester_name"],
                    requester_email=row["requester_email"],
                    ticket_count=int(row["ticket_count"] or 0),
                )
                for row in top_customer_rows
            ],
        )

    @staticmethod
    def _seconds_between(end_column: Any, start_column: Any) -> Any:
        return func.unix_timestamp(end_column) - func.unix_timestamp(start_column)

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        return round(float(value), 2) if value is not None else None
