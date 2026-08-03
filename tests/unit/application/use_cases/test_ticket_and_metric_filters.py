from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.application.contracts.repositories import CustomerRepository, TicketRepository
from src.application.dtos.analytics import (
    CustomerAnalyticsQueryPage,
    CustomerAnalyticsRow,
    CustomerMetricsInput,
)
from src.application.dtos.cursor_page import CursorPage
from src.application.dtos.list_customers import CustomerListItem, ListCustomersInput
from src.application.dtos.list_tickets import ListTicketsInput, TicketListItem
from src.application.use_cases.analytics import ListCustomerMetrics
from src.application.use_cases.list_customers import ListCustomers
from src.application.use_cases.list_tickets import ListTickets
from src.domain.entities import TicketPriority, TicketStatus


CUSTOMER_A = UUID("0198f17c-1a23-7000-8000-000000000001")
TICKET_A = UUID("0198f17c-1a23-7000-8000-000000000101")
pytestmark = pytest.mark.unit


def test_list_tickets_delegates_filters_and_search_once() -> None:
    asyncio.run(_run_ticket_list_scenario())


async def _run_ticket_list_scenario() -> None:
    item = TicketListItem(
        id=TICKET_A,
        external_ticket_id=1001,
        subject="Falha no domínio",
        status=TicketStatus.SOLVED,
        priority=TicketPriority.HIGH,
        assignee_name="Suporte N1",
        source_created_at=datetime(2026, 8, 2, 10, tzinfo=timezone.utc),
        source_updated_at=datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
    )
    page_list = AsyncMock(
        return_value=CursorPage[TicketListItem](
            items=[item],
            next_cursor=None,
            previous_cursor=None,
            has_next=False,
            has_previous=False,
        )
    )
    repository = cast(TicketRepository, SimpleNamespace(page_list=page_list))
    input_dto = ListTicketsInput(
        search="  falha   domínio  ",
        statuses=[TicketStatus.SOLVED],
        priorities=[TicketPriority.HIGH],
        from_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        to_at=datetime(2026, 8, 2, 23, 59, 59, tzinfo=timezone.utc),
        page_size=25,
    )

    output = await ListTickets(repository).execute(input_dto)

    assert output.page.items == [item]
    assert input_dto.search == "falha domínio"
    page_list.assert_awaited_once_with(input_dto)


def test_list_customers_delegates_global_search_once() -> None:
    asyncio.run(_run_customer_list_scenario())


async def _run_customer_list_scenario() -> None:
    item = CustomerListItem(
        id=CUSTOMER_A,
        external_requester_id=501,
        requester_name="Cliente A",
        requester_email="cliente@example.com",
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    page_list = AsyncMock(
        return_value=CursorPage[CustomerListItem](
            items=[item],
            next_cursor=None,
            previous_cursor=None,
            has_next=False,
            has_previous=False,
        )
    )
    repository = cast(CustomerRepository, SimpleNamespace(page_list=page_list))
    input_dto = ListCustomersInput(search="  Cliente   A ", page_size=25)

    output = await ListCustomers(repository).execute(input_dto)

    assert output.page.items == [item]
    assert input_dto.search == "Cliente A"
    page_list.assert_awaited_once_with(input_dto)


def test_customer_metrics_uses_one_repository_page_and_calculates_rates() -> None:
    asyncio.run(_run_customer_metric_scenario())


async def _run_customer_metric_scenario() -> None:
    query_page = CustomerAnalyticsQueryPage(
        items=[
            CustomerAnalyticsRow(
                customer_id=CUSTOMER_A,
                external_requester_id=101,
                requester_name="Cliente A",
                requester_email="a@example.com",
                ticket_volume=4,
                resolved_tickets=3,
                good_ratings=3,
                bad_ratings=1,
                average_first_response_seconds=600,
                average_recurrence_seconds=3600,
                recurrence_sample_intervals=3,
                top_topics=[],
            )
        ],
        page=1,
        page_size=25,
        total=1,
        has_next=False,
        has_previous=False,
    )
    page_customer_analytics = AsyncMock(return_value=query_page)
    repository = cast(
        TicketRepository,
        SimpleNamespace(page_customer_analytics=page_customer_analytics),
    )
    input_dto = CustomerMetricsInput(
        page=1,
        page_size=25,
        ticket_volume_min=2,
        satisfaction_rate_min=0.7,
    )

    output = await ListCustomerMetrics(repository).execute(input_dto)

    assert output.total == 1
    assert output.items[0].resolution_rate == pytest.approx(0.75)
    assert output.items[0].satisfaction_rate == pytest.approx(0.75)
    page_customer_analytics.assert_awaited_once_with(input_dto)


def test_filter_ranges_are_validated() -> None:
    with pytest.raises(ValidationError):
        ListTicketsInput(
            from_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
            to_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
    with pytest.raises(ValidationError):
        CustomerMetricsInput(ticket_volume_min=10, ticket_volume_max=5)
    with pytest.raises(ValidationError):
        CustomerMetricsInput(
            satisfaction_rate_min=0.9,
            satisfaction_rate_max=0.5,
        )
