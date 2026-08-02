from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.infra.ingestion.schemas import SourceBatch, TicketSourceRecord


class JsonTicketSourceRepository:
    """Read the complete JSON snapshot generated for the current worker cycle."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def read_all(self, *, expected_count: int | None = None) -> SourceBatch:
        raw_payload = json.loads(self._path.read_text(encoding="utf-8"))
        raw_records = self._extract_records(raw_payload)

        records: list[TicketSourceRecord] = []
        invalid = 0
        for raw_record in raw_records:
            try:
                records.append(TicketSourceRecord.model_validate(raw_record))
            except ValidationError:
                invalid += 1

        consumed = len(raw_records)
        if expected_count is not None and consumed != expected_count:
            raise ValueError(
                f"JSON source contains {consumed} records; expected {expected_count}"
            )

        return SourceBatch(
            version=hashlib.sha256(self._path.read_bytes()).hexdigest(),
            records=records,
            consumed=consumed,
            invalid=invalid,
            exhausted=True,
        )

    @staticmethod
    def _extract_records(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            payload = payload.get("tickets")
        if not isinstance(payload, list):
            raise ValueError("JSON source must contain a ticket array")
        if any(not isinstance(item, dict) for item in payload):
            raise ValueError("Every ticket source item must be a JSON object")
        return payload
