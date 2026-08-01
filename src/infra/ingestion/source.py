from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO

from pydantic import ValidationError

from src.infra.ingestion.schemas import SourceBatch, TicketSourceRecord


class JsonTicketSourceRepository:
    _CHUNK_SIZE = 64 * 1024
    _HEADER_LIMIT = 1024 * 1024

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._iterator: Iterator[dict[str, Any]] | None = None
        self._iterator_version: str | None = None
        self._iterator_cursor = 0

    def current_version(self) -> str:
        stat = self._path.stat()
        return f"{stat.st_mtime_ns}:{stat.st_size}"

    def read_batch(self, offset: int, limit: int) -> SourceBatch:
        if offset < 0:
            raise ValueError("Source offset cannot be negative")
        if limit <= 0:
            raise ValueError("Source batch limit must be positive")

        version = self.current_version()
        self._ensure_iterator(version=version, offset=offset)
        assert self._iterator is not None

        records: list[TicketSourceRecord] = []
        consumed = 0
        invalid = 0
        exhausted = False

        while consumed < limit:
            try:
                raw_record = next(self._iterator)
            except StopIteration:
                exhausted = True
                break

            consumed += 1
            self._iterator_cursor += 1
            try:
                records.append(TicketSourceRecord.model_validate(raw_record))
            except ValidationError:
                invalid += 1

        return SourceBatch(
            version=version,
            records=records,
            consumed=consumed,
            invalid=invalid,
            exhausted=exhausted,
        )

    def _ensure_iterator(self, *, version: str, offset: int) -> None:
        if (
            self._iterator is not None
            and self._iterator_version == version
            and self._iterator_cursor == offset
        ):
            return

        iterator = self._iter_raw_records()
        skipped = 0
        while skipped < offset:
            try:
                next(iterator)
            except StopIteration:
                break
            skipped += 1

        self._iterator = iterator
        self._iterator_version = version
        self._iterator_cursor = skipped

    def _iter_raw_records(self) -> Iterator[dict[str, Any]]:
        with self._path.open("r", encoding="utf-8") as stream:
            yield from self._decode_array(stream)

    def _decode_array(self, stream: TextIO) -> Iterator[dict[str, Any]]:
        decoder = json.JSONDecoder()
        buffer = self._read_array_prefix(stream)

        while True:
            buffer = buffer.lstrip()
            if not buffer:
                chunk = stream.read(self._CHUNK_SIZE)
                if not chunk:
                    raise ValueError("JSON source ended before the array was closed")
                buffer += chunk
                continue

            if buffer[0] == "]":
                return
            if buffer[0] == ",":
                buffer = buffer[1:]
                continue

            try:
                value, consumed = decoder.raw_decode(buffer)
            except json.JSONDecodeError:
                chunk = stream.read(self._CHUNK_SIZE)
                if not chunk:
                    raise ValueError("JSON source contains an incomplete record")
                buffer += chunk
                continue

            if not isinstance(value, dict):
                raise ValueError("Every ticket source item must be a JSON object")
            yield value
            buffer = buffer[consumed:]

    def _read_array_prefix(self, stream: TextIO) -> str:
        buffer = ""
        while len(buffer) <= self._HEADER_LIMIT:
            chunk = stream.read(self._CHUNK_SIZE)
            if not chunk:
                raise ValueError("JSON source does not contain a ticket array")
            buffer += chunk
            stripped = buffer.lstrip()
            if stripped.startswith("["):
                return stripped[1:]

            match = re.search(r'"tickets"\s*:\s*\[', buffer)
            if match:
                return buffer[match.end():]

        raise ValueError("JSON source header is too large")
