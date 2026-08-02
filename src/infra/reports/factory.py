from __future__ import annotations

from collections.abc import Mapping

from src.application.contracts.reports import ReportWriter, ReportWriterFactory
from src.domain.analytics import ReportFormat
from src.infra.reports.csv_writer import CsvReportWriter
from src.infra.reports.xlsx_writer import XlsxReportWriter

_DEFAULT_WRITERS: dict[ReportFormat, type[ReportWriter]] = {
    ReportFormat.CSV: CsvReportWriter,
    ReportFormat.XLSX: XlsxReportWriter,
}


class DefaultReportWriterFactory(ReportWriterFactory):
    def __init__(
        self,
        writers: Mapping[ReportFormat, type[ReportWriter]] | None = None,
    ) -> None:
        self._writers = dict(writers or _DEFAULT_WRITERS)

    def create(self, report_format: ReportFormat) -> ReportWriter:
        try:
            writer_type = self._writers[report_format]
        except KeyError as error:
            raise ValueError(
                f"unsupported report format: {report_format.value}"
            ) from error
        return writer_type()
