import json
from pathlib import Path

import pytest

from src.infra.workers.ticket_ingestion_worker import read_generated_tickets


pytestmark = pytest.mark.unit


def test_read_generated_tickets_validates_and_converts_snapshot(tmp_path: Path) -> None:
    source_path = tmp_path / "tickets.json"
    source_path.write_text(
        json.dumps(
            [
                {
                    "ticket_id": 1001,
                    "subject": "Falha de DNS",
                    "description": "O domínio não resolve.",
                    "status": "open",
                    "priority": "normal",
                    "requester_id": 501,
                    "requester_name": "Cliente A",
                    "requester_email": "CLIENTE@EXAMPLE.COM",
                    "created_at": "2026-08-01T10:00:00Z",
                    "updated_at": "2026-08-01T10:05:00Z",
                    "tags": ["dns"],
                }
            ]
        ),
        encoding="utf-8",
    )

    records = read_generated_tickets(source_path, expected_count=1)

    assert len(records) == 1
    assert records[0].ticket_id == 1001
    assert records[0].requester_email == "cliente@example.com"


@pytest.mark.parametrize("payload", [{"ticket_id": 1001}, []])
def test_read_generated_tickets_rejects_invalid_batch_shape(
    tmp_path: Path,
    payload: object,
) -> None:
    source_path = tmp_path / "tickets.json"
    source_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="exactly 1 records"):
        read_generated_tickets(source_path, expected_count=1)
