from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from src.application.dtos.analytics import AnalyticsFilters
from src.infra.database.dashboard_workspace import DashboardWorkspaceQueryRepository
from src.infra.database.models import Base
from src.infra.database.unit_of_work import UnitOfWork
from tests.fixtures.analytics_dataset import seed_analytics_dataset


@pytest.mark.skipif(
    not os.getenv("MYSQL_URL_CONNECTION_API", "").startswith("mysql+aiomysql://"),
    reason="requires a MySQL 8 test database",
)
def test_dashboard_workspace_returns_previous_period_and_complete_filter_options() -> None:
    asyncio.run(_run_scenario())


async def _run_scenario() -> None:
    engine = create_async_engine(os.environ["MYSQL_URL_CONNECTION_API"], pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

        records = [
            {
                "ticket_id": 200001,
                "requester_id": 200001,
                "requester_name": "Cliente 200001",
                "requester_email": "anterior@example.com",
                "created_at": "2026-07-09T12:00:00Z",
                "status": "solved",
                "priority": "high",
                "first_response_at": "2026-07-09T12:00:00Z",
                "assignee_id": 9103,
                "assignee_name": "Marina Alves (Domínios e DNS)",
                "tags": ["dns"],
                "satisfaction_rating": {
                    "score": "good",
                    "offered_at": "2026-07-09T12:00:00Z",
                    "rated_at": "2026-07-09T12:00:00Z",
                    "comment": "Resolvido",
                },
            },
            {
                "ticket_id": 200002,
                "requester_id": 200002,
                "requester_name": "Cliente 200002",
                "requester_email": "atual-a@example.com",
                "created_at": "2026-07-10T12:00:00Z",
                "status": "open",
                "priority": "high",
                "first_response_at": "2026-07-10T12:00:00Z",
                "assignee_id": 9103,
                "assignee_name": "Marina Alves (Domínios e DNS)",
                "tags": ["dns"],
                "satisfaction_rating": {
                    "score": "good",
                    "offered_at": "2026-07-10T12:00:00Z",
                    "rated_at": "2026-07-10T12:00:00Z",
                    "comment": "Resolvido",
                },
            },
            {
                "ticket_id": 200003,
                "requester_id": 200003,
                "requester_name": "Cliente 200003",
                "requester_email": "atual-b@example.com",
                "created_at": "2026-07-11T12:00:00Z",
                "status": "solved",
                "priority": "high",
                "first_response_at": "2026-07-11T12:00:00Z",
                "assignee_id": 9103,
                "assignee_name": "Marina Alves (Domínios e DNS)",
                "tags": ["ssl"],
                "satisfaction_rating": {
                    "score": "good",
                    "offered_at": "2026-07-11T12:00:00Z",
                    "rated_at": "2026-07-11T12:00:00Z",
                    "comment": "Resolvido",
                },
            },
        ]

        async with UnitOfWork(engine) as unit_of_work:
            await seed_analytics_dataset(unit_of_work, records)

        filters = AnalyticsFilters(
            from_at="2026-07-10T00:00:00Z",
            to_at="2026-07-12T00:00:00Z",
        )
        async with UnitOfWork(engine) as unit_of_work:
            dashboard = await DashboardWorkspaceQueryRepository(unit_of_work).get_dashboard(
                filters,
                top_topics_limit=8,
                timeline_limit=1,
            )

        volume = dashboard["metrics"]["ticket_volume"]
        assert volume["value"] == 2
        assert volume["previous_value"] == 1
        assert volume["change_percent"] == pytest.approx(100.0)
        assert dashboard["scope"]["is_comparable"] is True
        assert dashboard["scope"]["previous_from_at"] is not None
        assert len(dashboard["charts"]["operation_timeseries"]) == 1

        topics = {item["tag"]: item for item in dashboard["charts"]["top_topics"]}
        assert topics["dns"]["share"] == pytest.approx(0.5)
        assert topics["ssl"]["share"] == pytest.approx(0.5)
        assert dashboard["charts"]["priority_breakdown"][0]["share"] == pytest.approx(1.0)
        assert sum(
            item["share"] or 0
            for item in dashboard["charts"]["first_response_distribution"]
        ) == pytest.approx(1.0)

        options = dashboard["filter_options"]
        assert {item["name"] for item in options["tags"]} == {"dns", "ssl"}
        assert {item["requester_email"] for item in options["customers"]} == {
            "anterior@example.com",
            "atual-a@example.com",
            "atual-b@example.com",
        }
        assert options["assignees"] == [
            {"external_id": 9103, "name": "Marina Alves (Domínios e DNS)"}
        ]
        assert dashboard["summary"]["top_driver"]["label"] == "dns"
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()
