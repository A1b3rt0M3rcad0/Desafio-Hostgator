from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from src.application.dtos.analytics import AnalyticsFilters, CustomerMetricsInput
from src.application.dtos.ticket_ingestion import TicketSourceRecord
from src.infra.database.models import SatisfactionRating, Tag, Ticket, TicketTag
from src.infra.database.repositories import (
    SqlAlchemyCustomerRepository,
    SqlAlchemySatisfactionRatingRepository,
    SqlAlchemyTagRepository,
    SqlAlchemyTicketRepository,
    SqlAlchemyTicketTagRepository,
)
from src.infra.database.unit_of_work import UnitOfWork


pytestmark = pytest.mark.integration
UTC = timezone.utc


def _ticket_record(
    *,
    ticket_id: int,
    requester_id: int,
    requester_name: str,
    requester_email: str,
    created_at: datetime,
    status: str,
    tags: list[str],
    first_response_minutes: int | None,
    satisfaction_score: str | None,
) -> TicketSourceRecord:
    satisfaction = None
    if satisfaction_score is not None:
        satisfaction = {
            "score": satisfaction_score,
            "offered_at": created_at + timedelta(minutes=5),
            "rated_at": created_at + timedelta(minutes=45),
            "comment": f"Avaliação do ticket {ticket_id}",
        }
    return TicketSourceRecord.model_validate(
        {
            "ticket_id": ticket_id,
            "subject": f"Assunto do ticket {ticket_id}",
            "description": f"Descrição do ticket {ticket_id}",
            "status": status,
            "priority": "normal",
            "requester_id": requester_id,
            "requester_name": requester_name,
            "requester_email": requester_email,
            "assignee_id": 91,
            "assignee_name": "Suporte N1",
            "created_at": created_at,
            "updated_at": created_at + timedelta(hours=1),
            "first_response_at": (
                created_at + timedelta(minutes=first_response_minutes)
                if first_response_minutes is not None
                else None
            ),
            "tags": tags,
            "satisfaction_rating": satisfaction,
        }
    )


async def _persist_record(
    record: TicketSourceRecord,
    customers: SqlAlchemyCustomerRepository,
    tickets: SqlAlchemyTicketRepository,
    tags: SqlAlchemyTagRepository,
    ticket_tags: SqlAlchemyTicketTagRepository,
    ratings: SqlAlchemySatisfactionRatingRepository,
) -> UUID:
    customer_result = await customers.upsert_from_source(
        external_requester_id=record.requester_id,
        requester_name=record.requester_name,
        requester_email=record.requester_email,
    )
    customer_id = customer_result.customer.id
    assert customer_id is not None

    ticket_result = await tickets.upsert_from_source(
        record,
        customer_id=customer_id,
    )
    ticket_id = ticket_result.ticket.id
    assert ticket_id is not None

    resolved_tags = await tags.resolve_by_names(record.tags)
    await ticket_tags.replace_for_ticket(
        ticket_id=ticket_id,
        tag_ids=[tag.id for tag in resolved_tags.values() if tag.id is not None],
    )
    await ratings.synchronize_from_source(
        ticket_id=ticket_id,
        source=record.satisfaction_rating,
    )
    return ticket_id


@pytest.mark.asyncio
async def test_conflicting_customer_identity_rolls_back_batch(
    integration_engine: AsyncEngine,
) -> None:
    with pytest.raises(ValueError, match="belong to different customers"):
        async with UnitOfWork(integration_engine) as unit_of_work:
            customers = SqlAlchemyCustomerRepository(unit_of_work)
            await customers.upsert_from_source(
                external_requester_id=501,
                requester_name="Cliente A",
                requester_email="a@example.com",
            )
            await customers.upsert_from_source(
                external_requester_id=502,
                requester_name="Cliente B",
                requester_email="b@example.com",
            )
            await customers.upsert_from_source(
                external_requester_id=501,
                requester_name="Identidade conflitante",
                requester_email="b@example.com",
            )

    async with UnitOfWork(integration_engine) as unit_of_work:
        customers = SqlAlchemyCustomerRepository(unit_of_work)
        assert await customers.list_filter_options() == []


@pytest.mark.asyncio
async def test_ingestion_is_idempotent_and_analytics_execute_on_mysql(
    integration_engine: AsyncEngine,
) -> None:
    created_at = datetime(2026, 8, 1, 10, tzinfo=UTC)
    records = [
        _ticket_record(
            ticket_id=1001,
            requester_id=501,
            requester_name="Cliente A",
            requester_email="A@EXAMPLE.COM",
            created_at=created_at,
            status="open",
            tags=["dns"],
            first_response_minutes=10,
            satisfaction_score="good",
        ),
        _ticket_record(
            ticket_id=1002,
            requester_id=501,
            requester_name="Cliente A",
            requester_email="a@example.com",
            created_at=created_at + timedelta(hours=2),
            status="solved",
            tags=["dns", "ssl"],
            first_response_minutes=30,
            satisfaction_score="bad",
        ),
        _ticket_record(
            ticket_id=1003,
            requester_id=502,
            requester_name="Cliente B",
            requester_email="b@example.com",
            created_at=created_at + timedelta(days=1),
            status="closed",
            tags=["ssl"],
            first_response_minutes=None,
            satisfaction_score=None,
        ),
    ]

    async with UnitOfWork(integration_engine) as unit_of_work:
        customers = SqlAlchemyCustomerRepository(unit_of_work)
        tickets = SqlAlchemyTicketRepository(unit_of_work)
        tags = SqlAlchemyTagRepository(unit_of_work)
        ticket_tags = SqlAlchemyTicketTagRepository(unit_of_work)
        ratings = SqlAlchemySatisfactionRatingRepository(unit_of_work)
        for record in records:
            await _persist_record(
                record,
                customers,
                tickets,
                tags,
                ticket_tags,
                ratings,
            )

        customer = await customers.upsert_from_source(
            external_requester_id=501,
            requester_name="Cliente A",
            requester_email="a@example.com",
        )
        assert customer.customer.id is not None
        repeated_ticket = await tickets.upsert_from_source(
            records[0],
            customer_id=customer.customer.id,
        )
        assert repeated_ticket.created is False
        assert repeated_ticket.unchanged is True

        period = await tickets.get_dashboard_period_snapshot(
            AnalyticsFilters(),
            top_topics_limit=10,
        )
        operational = await tickets.get_dashboard_operational_snapshot(
            AnalyticsFilters(),
            timeline_limit=90,
        )
        customer_metrics = await tickets.page_customer_analytics(
            CustomerMetricsInput(page=1, page_size=25, top_topics_limit=2)
        )

        assert period.total_tickets == 3
        assert period.resolved_tickets == 2
        assert period.average_first_response_seconds == pytest.approx(1200)
        assert period.average_recurrence_seconds == pytest.approx(7200)
        assert period.recurrence_sample_intervals == 1
        assert {item.tag: item.ticket_count for item in period.topic_aggregates} == {
            "dns": 2,
            "ssl": 2,
        }

        assert operational.unique_customers == 2
        assert operational.repeat_customers == 1
        assert operational.average_tickets_per_customer == pytest.approx(1.5)
        assert sum(item.opened for item in operational.timeline) == 3
        assert {item.bucket: item.ticket_count for item in operational.response_buckets} == {
            "15_to_30m": 1,
            "unanswered": 1,
            "up_to_15m": 1,
        }

        assert customer_metrics.total == 2
        assert customer_metrics.items[0].requester_email == "a@example.com"
        assert customer_metrics.items[0].ticket_volume == 2
        assert customer_metrics.items[0].resolved_tickets == 1
        assert customer_metrics.items[0].average_recurrence_seconds == pytest.approx(
            7200
        )

    async with integration_engine.connect() as connection:
        assert (
            await connection.scalar(select(func.count()).select_from(Ticket))
        ) == 3
        assert (await connection.scalar(select(func.count()).select_from(Tag))) == 2
        assert (
            await connection.scalar(select(func.count()).select_from(TicketTag))
        ) == 4
        assert (
            await connection.scalar(
                select(func.count()).select_from(SatisfactionRating)
            )
        ) == 2
