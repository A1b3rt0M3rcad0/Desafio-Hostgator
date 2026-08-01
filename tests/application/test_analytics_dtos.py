import pytest
from pydantic import ValidationError

from src.application.dtos.analytics import AnalyticsFilters
from src.application.dtos.exports import DataExportInput, MetricsExportInput
from src.domain.analytics import DataExportField, MetricCode, ReportFormat
from src.domain.entities import TicketPriority, TicketStatus


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
