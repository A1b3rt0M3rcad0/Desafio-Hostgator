from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.application.dtos.ticket_ingestion import TicketSourceRecord
from src.domain.entities import SatisfactionScore, TicketPriority, TicketStatus


pytestmark = pytest.mark.unit


def _source_payload() -> dict[str, object]:
    return {
        "ticket_id": 1001,
        "subject": "Falha de DNS",
        "description": "O domínio não resolve.",
        "status": "solved",
        "priority": "high",
        "requester_id": 501,
        "requester_name": "Cliente A",
        "requester_email": "  CLIENTE@EXAMPLE.COM  ",
        "assignee_id": 91,
        "assignee_name": "Suporte N1",
        "created_at": datetime(2026, 8, 1, 10, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 8, 1, 12, tzinfo=timezone.utc),
        "first_response_at": datetime(2026, 8, 1, 10, 15, tzinfo=timezone.utc),
        "tags": [" ssl ", "dns", "dns", ""],
        "satisfaction_rating": {"score": "good", "comment": "Resolvido"},
    }


def test_ticket_source_record_normalizes_source_values() -> None:
    record = TicketSourceRecord.model_validate(_source_payload())

    assert record.requester_email == "cliente@example.com"
    assert record.status is TicketStatus.SOLVED
    assert record.priority is TicketPriority.HIGH
    assert record.tags == ["dns", "ssl"]
    assert record.satisfaction_rating is not None
    assert record.satisfaction_rating.score is SatisfactionScore.GOOD


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subject", ""),
        ("description", ""),
        ("requester_name", ""),
        ("status", "unknown"),
        ("priority", "critical"),
    ],
)
def test_ticket_source_record_rejects_invalid_required_values(
    field: str,
    value: object,
) -> None:
    payload = _source_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        TicketSourceRecord.model_validate(payload)
