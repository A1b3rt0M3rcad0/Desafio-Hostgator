from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, func, select

from src.application.dtos.analytics import (
    AssigneeFilterOption,
    CustomerAnalyticsQueryPage,
    CustomerAnalyticsRow,
    CustomerMetricsInput,
    TopicCount,
)
from src.domain.analytics import RESOLVED_STATUSES
from src.infra.database.models import (
    Customer,
    SatisfactionRating,
    Tag,
    Ticket,
    TicketTag,
)
from src.infra.database.repositories.tickets.base import TicketRepositoryMixinBase


class TicketCustomerAnalyticsMixin(TicketRepositoryMixinBase):
    async def page_customer_analytics(
        self,
        input_dto: CustomerMetricsInput,
    ) -> CustomerAnalyticsQueryPage:
        predicates = self._ticket_predicates(input_dto)
        valid_response = and_(
            Ticket.first_response_at.is_not(None),
            Ticket.first_response_at >= Ticket.source_created_at,
        )
        ticket_volume = func.count(Ticket.id)
        resolved_tickets = func.sum(
            case((Ticket.status.in_(RESOLVED_STATUSES), 1), else_=0)
        )
        good_ratings = func.sum(
            case((SatisfactionRating.score == "GOOD", 1), else_=0)
        )
        bad_ratings = func.sum(
            case((SatisfactionRating.score == "BAD", 1), else_=0)
        )
        customer_aggregates = (
            select(
                Customer.id.label("customer_id"),
                Customer.external_requester_id,
                Customer.requester_name,
                Customer.requester_email,
                ticket_volume.label("ticket_volume"),
                resolved_tickets.label("resolved_tickets"),
                good_ratings.label("good_ratings"),
                bad_ratings.label("bad_ratings"),
                func.avg(
                    case(
                        (
                            valid_response,
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
            .outerjoin(
                SatisfactionRating,
                SatisfactionRating.ticket_id == Ticket.id,
            )
            .where(*predicates)
            .group_by(
                Customer.id,
                Customer.external_requester_id,
                Customer.requester_name,
                Customer.requester_email,
            )
            .subquery()
        )
        rated_total = (
            customer_aggregates.c.good_ratings
            + customer_aggregates.c.bad_ratings
        )
        satisfaction_rate = (
            customer_aggregates.c.good_ratings / func.nullif(rated_total, 0)
        )
        metric_predicates: list[Any] = []
        if input_dto.ticket_volume_min is not None:
            metric_predicates.append(
                customer_aggregates.c.ticket_volume
                >= input_dto.ticket_volume_min
            )
        if input_dto.ticket_volume_max is not None:
            metric_predicates.append(
                customer_aggregates.c.ticket_volume
                <= input_dto.ticket_volume_max
            )
        if input_dto.satisfaction_rate_min is not None:
            metric_predicates.append(
                satisfaction_rate >= input_dto.satisfaction_rate_min
            )
        if input_dto.satisfaction_rate_max is not None:
            metric_predicates.append(
                satisfaction_rate <= input_dto.satisfaction_rate_max
            )

        filtered_customers = (
            select(
                customer_aggregates,
                satisfaction_rate.label("satisfaction_rate"),
            )
            .where(*metric_predicates)
            .subquery()
        )
        total_customers = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(filtered_customers)
                )
            ).scalar_one()
            or 0
        )
        offset = (input_dto.page - 1) * input_dto.page_size
        base_rows = (
            await self._session.execute(
                select(filtered_customers)
                .order_by(
                    filtered_customers.c.ticket_volume.desc(),
                    filtered_customers.c.requester_name.asc(),
                    filtered_customers.c.customer_id.asc(),
                )
                .offset(offset)
                .limit(input_dto.page_size)
            )
        ).mappings().all()
        page_customer_ids = [row["customer_id"] for row in base_rows]
        if not page_customer_ids:
            return CustomerAnalyticsQueryPage(
                items=[],
                page=input_dto.page,
                page_size=input_dto.page_size,
                total=total_customers,
                has_next=False,
                has_previous=input_dto.page > 1,
            )

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

        topic_counts = (
            select(
                Ticket.customer_id.label("customer_id"),
                Tag.name.label("tag"),
                func.count(func.distinct(Ticket.id)).label("ticket_count"),
            )
            .select_from(Ticket)
            .join(TicketTag, TicketTag.ticket_id == Ticket.id)
            .join(Tag, Tag.id == TicketTag.tag_id)
            .where(*predicates, Ticket.customer_id.in_(page_customer_ids))
            .group_by(Ticket.customer_id, Tag.id, Tag.name)
            .subquery()
        )
        ranked_topics = (
            select(
                topic_counts.c.customer_id,
                topic_counts.c.tag,
                topic_counts.c.ticket_count,
                func.row_number()
                .over(
                    partition_by=topic_counts.c.customer_id,
                    order_by=(
                        topic_counts.c.ticket_count.desc(),
                        topic_counts.c.tag.asc(),
                    ),
                )
                .label("topic_rank"),
            )
            .subquery()
        )
        topic_rows = (
            await self._session.execute(
                select(
                    ranked_topics.c.customer_id,
                    ranked_topics.c.tag,
                    ranked_topics.c.ticket_count,
                )
                .where(ranked_topics.c.topic_rank <= input_dto.top_topics_limit)
                .order_by(
                    ranked_topics.c.customer_id.asc(),
                    ranked_topics.c.topic_rank.asc(),
                )
            )
        ).mappings().all()
        topics_by_customer: dict[UUID, list[TopicCount]] = defaultdict(list)
        for row in topic_rows:
            topics_by_customer[row["customer_id"]].append(
                TopicCount(
                    tag=row["tag"],
                    ticket_count=int(row["ticket_count"] or 0),
                )
            )

        items: list[CustomerAnalyticsRow] = []
        for row in base_rows:
            customer_id = row["customer_id"]
            recurrence = recurrence_by_customer.get(customer_id, {})
            items.append(
                CustomerAnalyticsRow(
                    customer_id=customer_id,
                    external_requester_id=row["external_requester_id"],
                    requester_name=row["requester_name"],
                    requester_email=row["requester_email"],
                    ticket_volume=int(row["ticket_volume"] or 0),
                    resolved_tickets=int(row["resolved_tickets"] or 0),
                    good_ratings=int(row["good_ratings"] or 0),
                    bad_ratings=int(row["bad_ratings"] or 0),
                    average_first_response_seconds=self._optional_float(
                        row["average_first_response_seconds"]
                    ),
                    average_recurrence_seconds=self._optional_float(
                        recurrence.get("average_seconds")
                    ),
                    recurrence_sample_intervals=int(
                        recurrence.get("sample_intervals") or 0
                    ),
                    top_topics=topics_by_customer.get(customer_id, []),
                )
            )

        return CustomerAnalyticsQueryPage(
            items=items,
            page=input_dto.page,
            page_size=input_dto.page_size,
            total=total_customers,
            has_next=offset + len(items) < total_customers,
            has_previous=input_dto.page > 1,
        )

    async def list_assignee_options(self) -> list[AssigneeFilterOption]:
        rows = (
            await self._session.execute(
                select(Ticket.assignee_external_id, Ticket.assignee_name)
                .where(Ticket.assignee_external_id.is_not(None))
                .group_by(Ticket.assignee_external_id, Ticket.assignee_name)
                .order_by(Ticket.assignee_name.asc())
            )
        ).all()
        options: list[AssigneeFilterOption] = []
        for external_id, name in rows:
            if external_id is None:
                continue
            options.append(
                AssigneeFilterOption(external_id=external_id, name=name)
            )
        return options
