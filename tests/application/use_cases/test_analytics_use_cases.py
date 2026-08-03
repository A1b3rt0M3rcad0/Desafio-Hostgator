from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.application.contracts.repositories import (
    CustomerRepository,
    TagRepository,
    TicketRepository,
)
from src.application.dtos.analytics import (
    AnalyticsFilters,
    AssigneeFilterOption,
    CustomerAnalyticsQueryPage,
    CustomerAnalyticsRow,
    CustomerFilterOption,
    CustomerMetricsInput,
    DashboardInput,
    DashboardOperationalSnapshot,
    DashboardPeriodSnapshot,
    PriorityAggregate,
    ResponseBucketAggregate,
    StatusAggregate,
    TagFilterOption,
    TimelineAggregate,
    TopCustomerAggregate,
    TopicAggregate,
    TopicCount,
)
from src.application.use_cases.analytics import GetDashboardOverview, ListCustomerMetrics


CUSTOMER_ID = UUID("0198f17c-1a23-7000-8000-000000000001")
TAG_ID = UUID("0198f17c-1a23-7000-8000-000000000002")


def test_dashboard_use_case_orchestrates_repositories_and_owns_business_rules() -> None:
    asyncio.run(_run_dashboard_scenario())


async def _run_dashboard_scenario() -> None:
    current = DashboardPeriodSnapshot(
        total_tickets=2,
        resolved_tickets=1,
        average_first_response_seconds=900,
        responded_tickets=2,
        good_ratings=1,
        bad_ratings=1,
        average_recurrence_seconds=3600,
        recurrence_sample_intervals=1,
        customers_with_recurrence=1,
        status_counts=[
            StatusAggregate(label="OPEN", value=1),
            StatusAggregate(label="SOLVED", value=1),
        ],
        priority_aggregates=[
            PriorityAggregate(
                priority="HIGH",
                ticket_count=2,
                resolved_tickets=1,
                average_first_response_seconds=900,
            )
        ],
        topic_aggregates=[
            TopicAggregate(
                tag="dns",
                ticket_count=1,
                resolved_tickets=1,
                average_first_response_seconds=600,
            ),
            TopicAggregate(
                tag="ssl",
                ticket_count=1,
                resolved_tickets=0,
                average_first_response_seconds=1200,
            ),
        ],
    )
    previous = DashboardPeriodSnapshot(
        total_tickets=1,
        resolved_tickets=1,
        average_first_response_seconds=1200,
        responded_tickets=1,
        good_ratings=1,
        bad_ratings=0,
        average_recurrence_seconds=None,
        recurrence_sample_intervals=0,
        customers_with_recurrence=0,
        status_counts=[StatusAggregate(label="SOLVED", value=1)],
        priority_aggregates=[
            PriorityAggregate(
                priority="HIGH",
                ticket_count=1,
                resolved_tickets=1,
                average_first_response_seconds=1200,
            )
        ],
        topic_aggregates=[
            TopicAggregate(
                tag="dns",
                ticket_count=1,
                resolved_tickets=1,
                average_first_response_seconds=1200,
            )
        ],
    )
    operational = DashboardOperationalSnapshot(
        timeline=[
            TimelineAggregate(
                date="2026-07-11",
                opened=1,
                resolved=1,
                average_first_response_seconds=600,
                good_ratings=1,
                bad_ratings=0,
            )
        ],
        response_buckets=[
            ResponseBucketAggregate(bucket="up_to_15m", ticket_count=1),
            ResponseBucketAggregate(bucket="15_to_30m", ticket_count=1),
        ],
        unique_customers=1,
        repeat_customers=1,
        average_tickets_per_customer=2,
        top_customers=[
            TopCustomerAggregate(
                customer_id=CUSTOMER_ID,
                requester_name="Cliente",
                requester_email="cliente@example.com",
                ticket_count=2,
            )
        ],
    )

    get_dashboard_period_snapshot = AsyncMock(
        side_effect=[current, previous]
    )
    ticket_repository = cast(
        TicketRepository,
        SimpleNamespace(
            get_dashboard_period_snapshot=get_dashboard_period_snapshot,
            get_dashboard_operational_snapshot=AsyncMock(
                return_value=operational
            ),
            list_assignee_options=AsyncMock(
                return_value=[
                    AssigneeFilterOption(external_id=91, name=None)
                ]
            ),
        ),
    )
    customer_repository = cast(
        CustomerRepository,
        SimpleNamespace(
            list_filter_options=AsyncMock(
                return_value=[
                    CustomerFilterOption(
                        id=CUSTOMER_ID,
                        requester_name="Cliente",
                        requester_email="cliente@example.com",
                    )
                ]
            )
        ),
    )
    tag_repository = cast(
        TagRepository,
        SimpleNamespace(
            list_filter_options=AsyncMock(
                return_value=[TagFilterOption(id=TAG_ID, name="dns")]
            )
        ),
    )

    output = await GetDashboardOverview(
        ticket_repository=ticket_repository,
        customer_repository=customer_repository,
        tag_repository=tag_repository,
    ).execute(
        DashboardInput(
            from_at=datetime(2026, 7, 10, tzinfo=timezone.utc),
            to_at=datetime(2026, 7, 12, tzinfo=timezone.utc),
            timeline_limit=1,
            top_topics_limit=8,
        )
    )

    assert output.metrics.ticket_volume.value == 2
    assert output.metrics.ticket_volume.previous_value == 1
    assert output.metrics.ticket_volume.change_percent == pytest.approx(100)
    assert output.metrics.resolution_rate.rate == pytest.approx(0.5)
    assert output.metrics.resolution_rate.change_points == pytest.approx(-50)
    assert output.metrics.average_first_response.change_percent == pytest.approx(-25)

    assert len(output.charts.operation_timeseries) == 1
    assert output.charts.priority_breakdown[0].share == pytest.approx(1)
    assert [topic.share for topic in output.charts.top_topics] == pytest.approx([0.5, 0.5])
    assert sum(
        item.share or 0 for item in output.charts.first_response_distribution
    ) == pytest.approx(1)
    assert output.charts.top_topics[0].previous_ticket_count == 1
    assert output.charts.top_topics[1].previous_ticket_count == 0

    assert output.scope.is_comparable is True
    assert output.scope.previous_from_at is not None
    assert output.filter_options.assignees == [
        {"external_id": 91, "name": "Responsável 91"}
    ]
    assert output.summary.top_driver is not None
    assert output.summary.top_driver.label == "dns"

    assert get_dashboard_period_snapshot.await_count == 2
    previous_filters = cast(
        AnalyticsFilters,
        get_dashboard_period_snapshot.await_args_list[1].args[0],
    )
    assert previous_filters.to_at is not None
    assert output.scope.from_at is not None
    assert previous_filters.to_at < output.scope.from_at


def test_customer_metrics_use_case_calculates_rates_from_query_data() -> None:
    asyncio.run(_run_customer_metrics_scenario())


async def _run_customer_metrics_scenario() -> None:
    repository = cast(
        TicketRepository,
        SimpleNamespace(
            page_customer_analytics=AsyncMock(
                return_value=CustomerAnalyticsQueryPage(
                items=[
                    CustomerAnalyticsRow(
                        customer_id=CUSTOMER_ID,
                        external_requester_id=100,
                        requester_name="Cliente",
                        requester_email="cliente@example.com",
                        ticket_volume=3,
                        resolved_tickets=2,
                        good_ratings=1,
                        bad_ratings=1,
                        average_first_response_seconds=1200,
                        average_recurrence_seconds=3600,
                        recurrence_sample_intervals=2,
                        top_topics=[TopicCount(tag="dns", ticket_count=2)],
                    )
                ],
                page=1,
                page_size=25,
                total=1,
                has_next=False,
                has_previous=False,
                )
            ),
        ),
    )

    output = await ListCustomerMetrics(repository).execute(CustomerMetricsInput())

    assert output.items[0].resolution_rate == pytest.approx(2 / 3)
    assert output.items[0].satisfaction_rate == pytest.approx(0.5)
    assert output.items[0].top_topics[0].tag == "dns"
