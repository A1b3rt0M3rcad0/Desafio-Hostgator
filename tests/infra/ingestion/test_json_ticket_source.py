import json
from pathlib import Path

from src.infra.ingestion.source import JsonTicketSourceRepository


def ticket(ticket_id: int) -> dict:
    return {
        "ticket_id": ticket_id,
        "subject": f"Ticket {ticket_id}",
        "description": "Description",
        "status": "open",
        "priority": "normal",
        "requester_id": 100 + ticket_id,
        "requester_name": "Customer",
        "requester_email": f"customer{ticket_id}@example.com",
        "created_at": "2026-08-01T00:00:00Z",
        "updated_at": "2026-08-01T00:00:00Z",
        "tags": ["support", "support"],
    }


def test_reads_incremental_batches_from_array(tmp_path: Path) -> None:
    source_path = tmp_path / "tickets.json"
    source_path.write_text(json.dumps([ticket(index) for index in range(1, 61)]))
    repository = JsonTicketSourceRepository(source_path)

    first = repository.read_batch(0, 25)
    second = repository.read_batch(25, 25)
    third = repository.read_batch(50, 25)

    assert [record.ticket_id for record in first.records] == list(range(1, 26))
    assert [record.ticket_id for record in second.records] == list(range(26, 51))
    assert [record.ticket_id for record in third.records] == list(range(51, 61))
    assert third.exhausted is True


def test_supports_object_with_tickets_array(tmp_path: Path) -> None:
    source_path = tmp_path / "tickets.json"
    source_path.write_text(json.dumps({"tickets": [ticket(1), ticket(2)]}))
    repository = JsonTicketSourceRepository(source_path)

    batch = repository.read_batch(0, 25)

    assert [record.ticket_id for record in batch.records] == [1, 2]
    assert batch.exhausted is True


def test_invalid_records_advance_source_cursor(tmp_path: Path) -> None:
    source_path = tmp_path / "tickets.json"
    source_path.write_text(json.dumps([ticket(1), {"ticket_id": 2}, ticket(3)]))
    repository = JsonTicketSourceRepository(source_path)

    batch = repository.read_batch(0, 25)

    assert [record.ticket_id for record in batch.records] == [1, 3]
    assert batch.consumed == 3
    assert batch.invalid == 1
