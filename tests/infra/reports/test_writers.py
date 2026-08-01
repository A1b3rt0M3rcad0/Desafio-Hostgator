import csv
import io
import zipfile

from src.domain.analytics import ReportFormat
from src.infra.reports.writers import CsvReportWriter, DefaultReportWriterFactory, XlsxReportWriter


def test_supported_formats_do_not_include_legacy_xls() -> None:
    assert {item.value for item in ReportFormat} == {"csv", "xlsx"}


def test_csv_writer_serializes_nested_values_and_blocks_formulas() -> None:
    content = CsvReportWriter().write(
        [{"subject": "=SUM(1,1)", "tags": ["login", "portal"]}],
        ["subject", "tags"],
        "Tickets",
    )
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    assert rows[0]["subject"] == "'=SUM(1,1)"
    assert rows[0]["tags"] == '["login","portal"]'


def test_xlsx_writer_produces_valid_openxml_archive() -> None:
    content = XlsxReportWriter().write(
        [{"ticket_id": 100001, "subject": "Ticket válido"}],
        ["ticket_id", "subject"],
        "Tickets",
    )
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert "[Content_Types].xml" in archive.namelist()
        assert "xl/workbook.xml" in archive.namelist()
        assert "xl/worksheets/sheet1.xml" in archive.namelist()
        worksheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "ticket_id" in worksheet
    assert "Ticket válido" in worksheet


def test_report_writer_factory_selects_only_supported_writers() -> None:
    factory = DefaultReportWriterFactory()
    assert isinstance(factory.create(ReportFormat.CSV), CsvReportWriter)
    assert isinstance(factory.create(ReportFormat.XLSX), XlsxReportWriter)
