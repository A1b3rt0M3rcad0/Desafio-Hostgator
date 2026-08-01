from __future__ import annotations

import csv
import io
import json
import zipfile
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any
from xml.sax.saxutils import escape

from src.application.contracts.analytics import ReportWriter, ReportWriterFactory
from src.domain.analytics import ReportFormat


_DANGEROUS_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _serialize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _sanitize_spreadsheet_value(value: Any) -> str:
    serialized = _serialize(value)
    if serialized.startswith(_DANGEROUS_FORMULA_PREFIXES):
        return f"'{serialized}"
    return serialized


class CsvReportWriter(ReportWriter):
    def write(
        self,
        rows: Iterable[dict[str, Any]],
        columns: list[str],
        sheet_name: str,
    ) -> bytes:
        del sheet_name
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(
            buffer,
            fieldnames=columns,
            extrasaction="ignore",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {column: _sanitize_spreadsheet_value(row.get(column)) for column in columns}
            )
        return buffer.getvalue().encode("utf-8-sig")


class XlsxReportWriter(ReportWriter):
    """Small dependency-free XLSX writer for one tabular worksheet."""

    def write(
        self,
        rows: Iterable[dict[str, Any]],
        columns: list[str],
        sheet_name: str,
    ) -> bytes:
        safe_sheet_name = self._safe_sheet_name(sheet_name)
        worksheet_xml = self._worksheet(rows, columns)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._content_types())
            archive.writestr("_rels/.rels", self._root_relationships())
            archive.writestr("xl/workbook.xml", self._workbook(safe_sheet_name))
            archive.writestr("xl/_rels/workbook.xml.rels", self._workbook_relationships())
            archive.writestr("xl/styles.xml", self._styles())
            archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)
        return output.getvalue()

    def _worksheet(
        self,
        rows: Iterable[dict[str, Any]],
        columns: list[str],
    ) -> str:
        xml_rows = [self._row_xml(1, {column: column for column in columns}, columns, header=True)]
        for row_number, row in enumerate(rows, start=2):
            xml_rows.append(self._row_xml(row_number, row, columns, header=False))
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
            '<sheetFormatPr defaultRowHeight="15"/>'
            '<sheetData>'
            + "".join(xml_rows)
            + '</sheetData><autoFilter ref="A1:'
            + self._column_name(max(len(columns), 1))
            + '1"/><pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
            '</worksheet>'
        )

    def _row_xml(
        self,
        row_number: int,
        row: dict[str, Any],
        columns: list[str],
        header: bool,
    ) -> str:
        cells: list[str] = []
        style = ' s="1"' if header else ""
        for column_number, column in enumerate(columns, start=1):
            reference = f"{self._column_name(column_number)}{row_number}"
            value = escape(_sanitize_spreadsheet_value(row.get(column)), {'"': '&quot;'})
            cells.append(
                f'<c r="{reference}" t="inlineStr"{style}><is><t xml:space="preserve">{value}</t></is></c>'
            )
        return f'<row r="{row_number}">{"".join(cells)}</row>'

    @staticmethod
    def _column_name(index: int) -> str:
        name = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            name = chr(65 + remainder) + name
        return name or "A"

    @staticmethod
    def _safe_sheet_name(value: str) -> str:
        sanitized = "".join("_" if char in "[]:*?/\\" else char for char in value).strip()
        return (sanitized or "Relatorio")[:31]

    @staticmethod
    def _content_types() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '</Types>'
        )

    @staticmethod
    def _root_relationships() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _workbook(sheet_name: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="'
            + escape(sheet_name, {'"': '&quot;'})
            + '" sheetId="1" r:id="rId1"/></sheets></workbook>'
        )

    @staticmethod
    def _workbook_relationships() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>'
        )

    @staticmethod
    def _styles() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
            '</styleSheet>'
        )


class DefaultReportWriterFactory(ReportWriterFactory):
    def create(self, report_format: ReportFormat) -> ReportWriter:
        if report_format == ReportFormat.CSV:
            return CsvReportWriter()
        if report_format == ReportFormat.XLSX:
            return XlsxReportWriter()
        raise ValueError(f"unsupported report format: {report_format}")
