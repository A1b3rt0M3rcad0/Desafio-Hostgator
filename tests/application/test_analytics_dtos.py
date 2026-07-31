from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.application.dtos.analytics import AnalyticsFilters, MetricExportInput, RawExportInput
from src.application.dtos.imports import SyncTicketsInput
from src.domain.analytics import MetricCode, RawField, ReportFormat
from src.domain.entities import SatisfactionScore, TicketPriority, TicketStatus


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


def test_report_inputs_default_to_complete_catalogs() -> None:
    raw = RawExportInput(format=ReportFormat.CSV)
    metrics = MetricExportInput(format=ReportFormat.XLSX)
    assert raw.fields == list(RawField)
    assert metrics.metrics == list(MetricCode)


def test_import_dto_normalizes_mock_values() -> None:
    input_dto = SyncTicketsInput(
        tickets=[
            {
                "ticket_id": 100001,
                "subject": "Falha de login",
                "description": "Cliente não acessa o portal.",
                "status": "open",
                "priority": "high",
                "requester_id": 5001,
                "requester_name": "Cliente",
                "requester_email": "CLIENTE@EXEMPLO.COM",
                "assignee_id": 9101,
                "assignee_name": "Atendente",
                "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
                "updated_at": datetime(2026, 7, 1, 1, tzinfo=timezone.utc),
                "first_response_at": datetime(2026, 7, 1, 0, 10, tzinfo=timezone.utc),
                "tags": ["portal", "login", "login"],
                "satisfaction_rating": {
                    "score": "good",
                    "comment": "Resolvido",
                },
            }
        ]
    )
    ticket = input_dto.tickets[0]
    assert ticket.status == TicketStatus.OPEN
    assert ticket.priority == TicketPriority.HIGH
    assert ticket.requester_email == "cliente@exemplo.com"
    assert ticket.tags == ["login", "portal"]
    assert ticket.satisfaction_rating.score == SatisfactionScore.GOOD
