from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from src.application.dtos.analytics import AnalyticsFilters, CustomerMetricsInput
from src.domain.analytics import DataExportField
from src.infra.database.dashboard_analytics import DashboardAnalyticsQueryRepository
from src.infra.database.exports import SqlAlchemyDataExportRepository
from src.infra.database.models import Base
from src.infra.database.unit_of_work import UnitOfWork
from tests.fixtures.analytics_dataset import seed_analytics_dataset


@pytest.mark.skipif(
    not os.getenv("MYSQL_URL_CONNECTION_API", "").startswith("mysql+aiomysql://"),
    reason="requires a MySQL 8 test database",
)
def test_dashboard_customer_metrics_and_detailed_export_on_mysql() -> None:
    asyncio.run(_run_mysql_scenario())


async def _run_mysql_scenario() -> None:
    engine = create_async_engine(os.environ["MYSQL_URL_CONNECTION_API"], pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

        records = [
            {
                "ticket_id": 100001,
                "requester_id": 5001,
                "requester_name": "Cliente A",
                "requester_email": "cliente-a@example.com",
                "created_at": "2026-07-01T10:00:00Z",
                "updated_at": "2026-07-01T11:00:00Z",
                "status": "solved",
                "priority": "normal",
                "first_response_at": "2026-07-01T10:10:00Z",
                "assignee_id": 9101,
                "assignee_name": "Atendente N1",
                "tags": ["portal", "login"],
                "satisfaction_rating": {
                    "score": "good",
                    "offered_at": "2026-07-01T10:00:00Z",
                    "rated_at": "2026-07-01T11:00:00Z",
                    "comment": "Avaliação do atendimento",
                },
            },
            {
                "ticket_id": 100002,
                "requester_id": 5001,
                "requester_name": "Cliente A",
                "requester_email": "cliente-a@example.com",
                "created_at": "2026-07-02T10:00:00Z",
                "updated_at": "2026-07-02T11:00:00Z",
                "status": "open",
                "priority": "normal",
                "first_response_at": "2026-07-02T10:30:00Z",
                "assignee_id": 9101,
                "assignee_name": "Atendente N1",
                "tags": ["login"],
                "satisfaction_rating": {
                    "score": "bad",
                    "offered_at": "2026-07-02T10:00:00Z",
                    "rated_at": "2026-07-02T11:00:00Z",
                    "comment": "Avaliação do atendimento",
                },
            },
            {
                "ticket_id": 100003,
                "requester_id": 5001,
                "requester_name": "Cliente A",
                "requester_email": "cliente-a@example.com",
                "created_at": "2026-07-04T10:00:00Z",
                "updated_at": "2026-07-04T11:00:00Z",
                "status": "closed",
                "priority": "normal",
                "first_response_at": None,
                "assignee_id": 9102,
                "assignee_name": "Atendente N2",
                "tags": ["billing"],
                "satisfaction_rating": {
                    "score": "offered",
                    "offered_at": "2026-07-04T10:00:00Z",
                    "rated_at": None,
                    "comment": "",
                },
            },
            {
                "ticket_id": 100004,
                "requester_id": 5002,
                "requester_name": "Cliente B",
                "requester_email": "cliente-b@example.com",
                "created_at": "2026-07-03T10:00:00Z",
                "updated_at": "2026-07-03T12:00:00Z",
                "status": "solved",
                "priority": "normal",
                "first_response_at": "2026-07-03T11:00:00Z",
                "assignee_id": 9101,
                "assignee_name": "Atendente N1",
                "tags": ["login"],
                "satisfaction_rating": {
                    "score": "good",
                    "offered_at": "2026-07-03T10:00:00Z",
                    "rated_at": "2026-07-03T12:00:00Z",
                    "comment": "Avaliação do atendimento",
                },
            },
        ]

        async with UnitOfWork(engine) as unit_of_work:
            await seed_analytics_dataset(unit_of_work, records)

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

        async with UnitOfWork(engine) as unit_of_work:
            export_repository = SqlAlchemyDataExportRepository(unit_of_work)
            exported_rows = await export_repository.fetch_rows(
                AnalyticsFilters(),
                list(DataExportField),
                limit=10,
                offset=0,
            )
            filtered_rows = await export_repository.fetch_rows(
                AnalyticsFilters(
                    statuses=["solved"],
                    tag_names=["login"],
                    assignee_external_ids=[9101],
                ),
                [DataExportField.TICKET_ID, DataExportField.STATUS],
                limit=10,
                offset=0,
            )
            options = await export_repository.get_filter_options()

        metrics = dashboard["metrics"]
        assert metrics["ticket_volume"]["value"] == 4
        assert metrics["ticket_volume"]["previous_value"] is None
        assert metrics["resolution_rate"]["rate"] == pytest.approx(0.75)
        assert metrics["resolution_rate"]["resolved"] == 3
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

        assert customer_metrics["total"] == 2
        customer_a = next(
            item for item in customer_metrics["items"]
            if item["requester_email"] == "cliente-a@example.com"
        )
        assert customer_a["ticket_volume"] == 3
        assert customer_a["resolution_rate"] == pytest.approx(2 / 3)
        assert customer_a["satisfaction_rate"] == pytest.approx(0.5)
        assert customer_a["average_first_response_seconds"] == pytest.approx(1200)
        assert customer_a["average_recurrence_seconds"] == pytest.approx(129600)

        assert [row["ticket_id"] for row in exported_rows] == [100001, 100002, 100003, 100004]
        assert exported_rows[0]["status"] == "solved"
        assert exported_rows[0]["tags"] == ["login", "portal"]
        assert exported_rows[0]["satisfaction_rating"]["score"] == "good"
        assert exported_rows[0]["created_at"].endswith("Z")
        assert filtered_rows == [{"ticket_id": 100001, "status": "solved"}, {"ticket_id": 100004, "status": "solved"}]
        assert {item["name"] for item in options["tags"]} == {"billing", "login", "portal"}
        assert len(options["customers"]) == 2
        assert len(options["assignees"]) == 2
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()
