import asyncio

import pytest
from pydantic import ValidationError

from src.application.dtos.analytics import AnalyticsFilters
from src.application.dtos.exports import DataExportInput, MetricsExportInput
from src.application.use_cases.exports import GetExportCatalog
from src.domain.analytics import DataExportField, MetricCode, ReportFormat
from src.domain.entities import TicketPriority, TicketStatus


class _CatalogRepository:
    async def get_filter_options(self) -> dict[str, list[dict[str, object]]]:
        return {"tags": [], "customers": [], "assignees": []}


def test_analytics_filters_normalize_comma_separated_values() -> None:
    filters = AnalyticsFilters(
        requester_emails="CLIENTE@EXEMPLO.COM, outro@exemplo.com",
        statuses="open,solved",
        priorities="high",
        tag_names="login,portal",
        has_first_response="false",
    )
    assert filters.requester_emails == ["cliente@exemplo.com", "outro@exemplo.com"]
    assert filters.statuses == [TicketStatus.OPEN, TicketStatus.SOLVED]
    assert filters.priorities == [TicketPriority.HIGH]
    assert filters.tag_names == ["login", "portal"]
    assert filters.has_first_response is False


def test_analytics_filters_reject_inverted_period() -> None:
    with pytest.raises(ValidationError):
        AnalyticsFilters(
            from_at="2026-08-01T00:00:00Z",
            to_at="2026-07-01T00:00:00Z",
        )


def test_export_inputs_default_to_complete_catalogs() -> None:
    data_export = DataExportInput(format=ReportFormat.CSV)
    metrics_export = MetricsExportInput(format=ReportFormat.XLSX)
    assert data_export.fields == list(DataExportField)
    assert metrics_export.metrics == list(MetricCode)


def test_export_filters_preserve_same_analytics_contract() -> None:
    data_export = DataExportInput(
        format="csv",
        filters={
            "statuses": ["open"],
            "priorities": ["urgent"],
            "requester_emails": ["CLIENTE@EXEMPLO.COM"],
        },
        fields=["ticket_id", "status"],
    )
    assert data_export.filters.statuses == [TicketStatus.OPEN]
    assert data_export.filters.priorities == [TicketPriority.URGENT]
    assert data_export.filters.requester_emails == ["cliente@exemplo.com"]
    assert data_export.fields == [DataExportField.TICKET_ID, DataExportField.STATUS]


def test_export_catalog_exposes_guided_defaults_and_field_presets() -> None:
    catalog = asyncio.run(GetExportCatalog(_CatalogRepository()).execute())

    assert catalog["defaults"] == {
        "data_format": "csv",
        "metrics_format": "xlsx",
        "period_days": 30,
        "field_preset": "essential",
        "scope": "overall",
        "metrics": [metric.value for metric in MetricCode],
    }

    presets = {item["code"]: item for item in catalog["field_presets"]}
    assert set(presets) == {"essential", "service", "complete"}
    assert presets["essential"]["fields"] == [
        "ticket_id",
        "subject",
        "status",
        "priority",
        "requester_name",
        "assignee_name",
        "created_at",
        "first_response_at",
        "tags",
        "satisfaction_rating",
    ]
    assert presets["complete"]["fields"] == [field.value for field in DataExportField]
