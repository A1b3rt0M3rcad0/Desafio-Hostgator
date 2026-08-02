from __future__ import annotations

import csv
import io
from collections.abc import Iterable

from src.application.contracts.reports import ReportRow, ReportWriter
from src.infra.reports.serialization import serialize_cell


class CsvReportWriter(ReportWriter):
    def write(
        self,
        rows: Iterable[ReportRow],
        columns: list[str],
        sheet_name: str,
    ) -> bytes:
        del sheet_name
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
