from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable
from xml.sax.saxutils import escape

from src.application.contracts.reports import ReportRow, ReportWriter
from src.infra.reports.serialization import serialize_cell

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

_ROOT_RELATIONSHIPS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_WORKBOOK_RELATIONSHIPS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""


class XlsxReportWriter(ReportWriter):
    def write(
        self,
        rows: Iterable[ReportRow],
        columns: list[str],
        sheet_name: str,
    ) -> bytes:
        if not columns:
            raise ValueError("XLSX report requires at least one column")

        output = io.BytesIO()
        with zipfile.ZipFile(
            output,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
            archive.writestr("_rels/.rels", _ROOT_RELATIONSHIPS)
            archive.writestr("xl/workbook.xml", _workbook_xml(sheet_name))
            archive.writestr(
                "xl/_rels/workbook.xml.rels",
                _WORKBOOK_RELATIONSHIPS,
            )
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                _worksheet_xml(rows, columns),
            )
        return output.getvalue()


def _workbook_xml(sheet_name: str) -> str:
    safe_name = "".join(
        "_" if character in "[]:*?/\\" else character
        for character in sheet_name
    ).strip()
    safe_name = escape((safe_name or "Relatorio")[:31], {'"': "&quot;"})
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{safe_name}" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )


def _worksheet_xml(
    rows: Iterable[ReportRow],
    columns: list[str],
) -> str:
    header = {column: column for column in columns}
    xml_rows = [_row_xml(1, header, columns)]
    xml_rows.extend(
        _row_xml(row_number, row, columns)
        for row_number, row in enumerate(rows, start=2)
    )
    last_column = _column_name(len(columns))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        f'<autoFilter ref="A1:{last_column}1"/>'
        '</worksheet>'
    )


def _row_xml(
    row_number: int,
    row: ReportRow,
    columns: list[str],
) -> str:
    cells = "".join(
        _cell_xml(
            reference=f"{_column_name(column_number)}{row_number}",
            value=serialize_cell(row.get(column)),
        )
        for column_number, column in enumerate(columns, start=1)
    )
    return f'<row r="{row_number}">{cells}</row>'


def _cell_xml(*, reference: str, value: str) -> str:
    safe_value = escape(value)
    return (
        f'<c r="{reference}" t="inlineStr">'
        f'<is><t xml:space="preserve">{safe_value}</t></is>'
        '</c>'
    )


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name
