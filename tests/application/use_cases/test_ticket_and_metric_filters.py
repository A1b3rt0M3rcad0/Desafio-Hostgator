from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.application.contracts.repositories import TicketRepository
from src.application.dtos.analytics import (
    CustomerAnalyticsQueryPage,
    CustomerAnalyticsRow,
    CustomerMetricsInput,
)
from src.application.dtos.cursor_page import CursorPage
from src.application.dtos.list_tickets import ListTicketsInput
from src.application.use_cases.analytics import ListCustomerMetrics
from src.application.use_cases.list_tickets import ListTickets
from src.domain.entities import (
    TicketEntity,
    TicketPriority,
    TicketStatus,
)


CUSTOMER_A = UUID("0198f17c-1a23-7000-8000-000000000001")
CUSTOMER_B = UUID("0198f17c-1a23-7000-8000-000000000002")
CUSTOMER_C = UUID("0198f17c-1a23-7000-8000-000000000003")


def _ticket(
    *,
    ticket_id: int,
    entity_id: str,
    status: TicketStatus,
    priority: TicketPriority,
    created_at: datetime,
) -> TicketEntity:
    return TicketEntity(
        id=UUID(entity_id),
        customer_id=CUSTOMER_A,
        external_ticket_id=ticket_id,
        subject=f"Ticket {ticket_id}",
        description="Descrição",
        status=status,
        priority=priority,
        source_created_at=created_at,
        source_updated_at=created_at,
    )


def test_list_tickets_applies_status_priority_and_created_at_filters() -> None:
    asyncio.run(_run_ticket_filter_scenario())


async def _run_ticket_filter_scenario() -> None:
    tickets = [
        _ticket(
            ticket_id=1,
            entity_id="0198f17c-1a23-7000-8000-000000000101",
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
            created_at=datetime(2026, 8, 1, 10, tzinfo=timezone.utc),
        ),
        _ticket(
            ticket_id=2,
            entity_id="0198f17c-1a23-7000-8000-000000000102",
            status=TicketStatus.SOLVED,
            priority=TicketPriority.HIGH,
            created_at=datetime(2026, 8, 2, 10, tzinfo=timezone.utc),
        ),
        _ticket(
            ticket_id=3,
            entity_id="0198f17c-1a23-7000-8000-000000000103",
            status=TicketStatus.SOLVED,
            priority=TicketPriority.LOW,
            created_at=datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
        ),
    ]
    page = AsyncMock(
        return_value=CursorPage[TicketEntity](
            items=tickets,
            next_cursor=None,
            previous_cursor=None,
            has_next=False,
            has_previous=False,
        )
    )
    repository = cast(
        TicketRepository,
        SimpleNamespace(page=page),
    )

    output = await ListTickets(repository).execute(
        ListTicketsInput(
            statuses=[TicketStatus.SOLVED],
            priorities=[TicketPriority.HIGH],
            from_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
            to_at=datetime(2026, 8, 2, 23, 59, 59, tzinfo=timezone.utc),
        )
    )

    assert [item.external_ticket_id for item in output.page.items] == [2]
    page.assert_awaited_once_with(None, 100)


def test_customer_metrics_filters_volume_and_satisfaction_before_pagination() -> None:
    asyncio.run(_run_customer_metric_filter_scenario())


async def _run_customer_metric_filter_scenario() -> None:
    first_page = CustomerAnalyticsQueryPage(
        items=[
            CustomerAnalyticsRow(
                customer_id=CUSTOMER_A,
                external_requester_id=101,
                requester_name="Cliente A",
                requester_email="a@example.com",
                ticket_volume=3,
                resolved_tickets=2,
                good_ratings=3,
                bad_ratings=1,
                average_first_response_seconds=600,
                average_recurrence_seconds=3600,
                recurrence_sample_intervals=2,
                top_topics=[],
            ),
            CustomerAnalyticsRow(
                customer_id=CUSTOMER_B,
                external_requester_id=102,
                requester_name="Cliente B",
                requester_email="b@example.com",
                ticket_volume=5,
                resolved_tickets=3,
                good_ratings=0,
                bad_ratings=0,
                average_first_response_seconds=900,
                average_recurrence_seconds=7200,
                recurrence_sample_intervals=4,
                top_topics=[],
            ),
        ],
        page=1,
        page_size=100,
        total=3,
        has_next=True,
        has_previous=False,
    )
    second_page = CustomerAnalyticsQueryPage(
        items=[
            CustomerAnalyticsRow(
                customer_id=CUSTOMER_C,
                external_requester_id=103,
                requester_name="Cliente C",
                requester_email="c@example.com",
                ticket_volume=1,
                resolved_tickets=1,
                good_ratings=1,
                bad_ratings=0,
                average_first_response_seconds=300,
                average_recurrence_seconds=None,
                recurrence_sample_intervals=0,
                top_topics=[],
            )
        ],
        page=2,
        page_size=100,
        total=3,
        has_next=False,
        has_previous=True,
    )
    page_customer_analytics = AsyncMock(side_effect=[first_page, second_page])
    repository = cast(
        TicketRepository,
        SimpleNamespace(page_customer_analytics=page_customer_analytics),
    )

    output = await ListCustomerMetrics(repository).execute(
        CustomerMetricsInput(
            page=1,
            page_size=1,
            ticket_volume_min=2,
            satisfaction_rate_min=0.75,
        )
    )

    assert output.total == 1
    assert [item.customer_id for item in output.items] == [CUSTOMER_A]
    assert output.items[0].satisfaction_rate == pytest.approx(0.75)
    assert output.has_next is False
    assert page_customer_analytics.await_count == 2
    assert page_customer_analytics.await_args_list[0].args[0].page_size == 100


def test_metric_filter_ranges_are_validated() -> None:
    with pytest.raises(ValidationError):
        CustomerMetricsInput(ticket_volume_min=10, ticket_volume_max=5)
    with pytest.raises(ValidationError):
        CustomerMetricsInput(
            satisfaction_rate_min=0.9,
            satisfaction_rate_max=0.5,
        )
