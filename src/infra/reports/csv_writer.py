from __future__ import annotations

import csv
import io
from collections.abc import AsyncIterator, Iterable

from src.application.contracts.reports import (
    ReportRow,
    ReportRowBatches,
    ReportWriter,
    StreamingReportWriter,
)
from src.infra.reports.serialization import serialize_cell


class CsvReportWriter(ReportWriter):
    def write(
        self,
        rows: Iterable[ReportRow],
        columns: list[str],
        sheet_name: str,
    ) -> bytes:
        del sheet_name
        if not columns:
            raise ValueError("CSV report requires at least one column")

        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(
            buffer,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {column: serialize_cell(row.get(column)) for column in columns}
            )
        return buffer.getvalue().encode("utf-8-sig")


class CsvStreamingReportWriter(StreamingReportWriter):
    async def write(
        self,
        row_batches: ReportRowBatches,
        columns: list[str],
        sheet_name: str,
    ) -> AsyncIterator[bytes]:
        del sheet_name
        if not columns:
            raise ValueError("CSV report requires at least one column")
        return self._stream(row_batches, columns)

    async def _stream(
        self,
        row_batches: ReportRowBatches,
        columns: list[str],
    ) -> AsyncIterator[bytes]:
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(
            buffer,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()
        yield buffer.getvalue().encode("utf-8-sig")

        async for rows in row_batches:
            buffer.seek(0)
            buffer.truncate(0)
            for row in rows:
                writer.writerow(
                    {
                        column: serialize_cell(row.get(column))
                        for column in columns
                    }
                )
            payload = buffer.getvalue()
            if payload:
                yield payload.encode("utf-8")
