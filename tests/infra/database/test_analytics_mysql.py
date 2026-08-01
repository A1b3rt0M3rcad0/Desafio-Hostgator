from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from src.application.dtos.analytics import AnalyticsFilters, CustomerMetricsInput
from src.application.dtos.imports import SyncTicketsInput
from src.domain.analytics import RawField
from src.infra.database.dashboard_analytics import DashboardAnalyticsQueryRepository
from src.infra.database.imports import SqlAlchemyTicketImportRepository
from src.infra.database.models import Base
from src.infra.database.unit_of_work import UnitOfWork


def _ticket(
    ticket_id: int,
    requester_id: int,
    requester_name: str,
    requester_email: str,
    created_at: str,
    updated_at: str,
    status: str,
    first_response_at: str | None,
    score: str,
    tags: list[str],
) -> dict[str, object]:
    return {
        "ticket_id": ticket_id,
        "subject": f"Ticket {ticket_id}",
        "description": f"Descrição do ticket {ticket_id}",
        "status": status,
        "priority": "normal",
        "requester_id": requester_id,
        "requester_name": requester_name,
        "requester_email": requester_email,
        "assignee_id": 9101,
        "assignee_name": "Atendente N1",
        "created_at": created_at,
        "updated_at": updated_at,
        "first_response_at": first_response_at,
        "tags": tags,
        "satisfaction_rating": {
            "score": score,
            "offered_at": created_at,
            "rated_at": updated_at if score in {"good", "bad"} else None,
            "comment": "Avaliação do atendimento",
        },
    }


@pytest.mark.skipif(
    not os.getenv("MYSQL_URL_CONNECTION_API", "").startswith("mysql+aiomysql://"),
    reason="requires a MySQL 8 test database",
)
def test_import_dashboard_customer_metrics_and_raw_reconstruction_on_mysql() -> None:
    asyncio.run(_run_mysql_scenario())


async def _run_mysql_scenario() -> None:
    engine = create_async_engine(os.environ["MYSQL_URL_CONNECTION_API"], pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

        records = SyncTicketsInput(
            tickets=[
                _ticket(
                    100001,
                    5001,
                    "Cliente A",
                    "cliente-a@example.com",
                    "2026-07-01T10:00:00Z",
                    "2026-07-01T11:00:00Z",
                    "solved",
                    "2026-07-01T10:10:00Z",
                    "good",
                    ["portal", "login"],
                ),
                _ticket(
                    100002,
                    5001,
                    "Cliente A",
                    "cliente-a@example.com",
                    "2026-07-02T10:00:00Z",
                    "2026-07-02T11:00:00Z",
                    "open",
                    "2026-07-02T10:30:00Z",
                    "bad",
                    ["login"],
                ),
                _ticket(
                    100003,
                    5001,
                    "Cliente A",
                    "cliente-a@example.com",
                    "2026-07-04T10:00:00Z",
                    "2026-07-04T11:00:00Z",
                    "closed",
                    None,
                    "offered",
                    ["billing"],
                ),
                _ticket(
                    100004,
                    5002,
                    "Cliente B",
                    "cliente-b@example.com",
                    "2026-07-03T10:00:00Z",
                    "2026-07-03T12:00:00Z",
                    "solved",
                    "2026-07-03T11:00:00Z",
                    "good",
                    ["login"],
                ),
            ]
        ).tickets

        async with UnitOfWork(engine) as unit_of_work:
            importer = SqlAlchemyTicketImportRepository(unit_of_work)
            first_import = await importer.sync(records)
        assert first_import.created == 4
        assert first_import.updated == 0
        assert first_import.customers_created == 2
        assert first_import.tags_created == 3

        async with UnitOfWork(engine) as unit_of_work:
            importer = SqlAlchemyTicketImportRepository(unit_of_work)
            repeated_import = await importer.sync(records)
        assert repeated_import.created == 0
        assert repeated_import.updated == 0
        assert repeated_import.unchanged == 4

        async with UnitOfWork(engine) as unit_of_work:
            analytics = DashboardAnalyticsQueryRepository(unit_of_work)
            dashboard = await analytics.get_dashboard(
                AnalyticsFilters(),
                top_topics_limit=10,
                timeline_limit=90,
            )
            customer_metrics = await analytics.list_customer_metrics(
                CustomerMetricsInput(page=1, page_size=25, top_topics_limit=3)
            )
            raw_rows = await analytics.fetch_raw_rows(
                AnalyticsFilters(),
                list(RawField),
                limit=10,
                offset=0,
            )

        metrics = dashboard["metrics"]
        assert metrics["ticket_volume"]["value"] == 4
        assert metrics["ticket_volume"]["previous_value"] is None
        assert metrics["resolution_rate"] == {
            "rate": pytest.approx(0.75),
            "resolved": 3,
            "total": 4,
            "previous_rate": None,
            "change_percent": None,
            "change_points": None,
        }
        assert metrics["satisfaction_rate"]["rate"] == pytest.approx(2 / 3)
        assert metrics["satisfaction_rate"]["good"] == 2
        assert metrics["satisfaction_rate"]["bad"] == 1
        assert metrics["average_first_response"]["average_seconds"] == pytest.approx(2000)
        assert metrics["average_recurrence"]["average_seconds"] == pytest.approx(129600)
        assert metrics["average_recurrence"]["sample_intervals"] == 2
        assert metrics["average_recurrence"]["customers_with_recurrence"] == 1

        assert dashboard["charts"]["top_topics"][0]["tag"] == "login"
        assert dashboard["charts"]["top_topics"][0]["ticket_count"] == 3
        assert dashboard["charts"]["top_topics"][0]["resolution_rate"] == pytest.approx(2 / 3)
        assert len(dashboard["charts"]["operation_timeseries"]) == 4
        assert sum(item["ticket_count"] for item in dashboard["charts"]["first_response_distribution"]) == 4
        assert dashboard["charts"]["priority_breakdown"][0]["ticket_count"] == 4
        assert dashboard["customer_behavior"]["unique_customers"] == 2
        assert dashboard["customer_behavior"]["repeat_customers"] == 1
        assert dashboard["customer_behavior"]["repeat_customer_rate"] == pytest.approx(0.5)
        assert dashboard["customer_behavior"]["top_customers"][0]["requester_email"] == "cliente-a@example.com"
        assert dashboard["summary"]["top_driver"]["label"] == "login"
        assert dashboard["scope"]["is_comparable"] is False

        assert customer_metrics["total"] == 2
        customer_a = next(
            item for item in customer_metrics["items"] if item["requester_email"] == "cliente-a@example.com"
        )
        assert customer_a["ticket_volume"] == 3
        assert customer_a["resolution_rate"] == pytest.approx(2 / 3)
        assert customer_a["satisfaction_rate"] == pytest.approx(0.5)
        assert customer_a["average_first_response_seconds"] == pytest.approx(1200)
        assert customer_a["average_recurrence_seconds"] == pytest.approx(129600)

        assert [row["ticket_id"] for row in raw_rows] == [100001, 100002, 100003, 100004]
        assert raw_rows[0]["status"] == "solved"
        assert raw_rows[0]["tags"] == ["login", "portal"]
        assert raw_rows[0]["satisfaction_rating"]["score"] == "good"
        assert raw_rows[0]["created_at"].endswith("Z")
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()
