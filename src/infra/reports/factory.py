from __future__ import annotations

from collections.abc import Mapping

from src.application.contracts.reports import (
    ReportWriter,
    ReportWriterFactory,
    StreamingReportWriter,
)
from src.domain.analytics import ReportFormat
from src.infra.reports.csv_writer import CsvReportWriter, CsvStreamingReportWriter
from src.infra.reports.xlsx_writer import XlsxReportWriter, XlsxStreamingReportWriter

_DEFAULT_WRITERS: dict[ReportFormat, type[ReportWriter]] = {
    ReportFormat.CSV: CsvReportWriter,
    ReportFormat.XLSX: XlsxReportWriter,
}

_DEFAULT_STREAMING_WRITERS: dict[ReportFormat, type[StreamingReportWriter]] = {
    ReportFormat.CSV: CsvStreamingReportWriter,
    ReportFormat.XLSX: XlsxStreamingReportWriter,
}


class DefaultReportWriterFactory(ReportWriterFactory):
    def __init__(
        self,
        writers: Mapping[ReportFormat, type[ReportWriter]] | None = None,
        streaming_writers: (
            Mapping[ReportFormat, type[StreamingReportWriter]] | None
        ) = None,
    ) -> None:
        self._writers = dict(_DEFAULT_WRITERS if writers is None else writers)
        self._streaming_writers = dict(
            _DEFAULT_STREAMING_WRITERS
            if streaming_writers is None
            else streaming_writers
        )

    def create(self, report_format: ReportFormat) -> ReportWriter:
        try:
            writer_type = self._writers[report_format]
        except KeyError as error:
            raise ValueError(
                f"unsupported report format: {report_format.value}"
            ) from error
        return writer_type()

    def create_streaming(
        self,
        report_format: ReportFormat,
    ) -> StreamingReportWriter:
        try:
            writer_type = self._streaming_writers[report_format]
        except KeyError as error:
            raise ValueError(
                f"unsupported streaming report format: {report_format.value}"
            ) from error
        return writer_type()
