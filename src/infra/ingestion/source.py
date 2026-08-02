from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.application.dtos.ticket_ingestion import TicketSourceRecord


def read_ticket_source(
    path: str | Path,
    *,
    expected_count: int | None = None,
) -> list[TicketSourceRecord]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_records = _extract_records(payload)

    if expected_count is not None and len(raw_records) != expected_count:
        raise ValueError(
            f"JSON source contains {len(raw_records)} records; "
            f"expected {expected_count}"
        )

    records = [TicketSourceRecord.model_validate(item) for item in raw_records]
    ticket_ids = [record.ticket_id for record in records]
    if len(ticket_ids) != len(set(ticket_ids)):
        raise ValueError("JSON source contains duplicated ticket IDs")
    return records


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get("tickets")
    if not isinstance(payload, list):
        raise ValueError("JSON source must contain a ticket array")
    if any(not isinstance(item, dict) for item in payload):
        raise ValueError("Every ticket source item must be a JSON object")
    return payload
