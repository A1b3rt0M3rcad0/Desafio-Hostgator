from __future__ import annotations

import asyncio
import io
import os
import tempfile
import zipfile
from collections.abc import AsyncIterator, Iterable
from pathlib import Path
from xml.sax.saxutils import escape

from src.application.contracts.reports import (
    ReportRow,
    ReportRowBatches,
    ReportWriter,
    StreamingReportWriter,
)
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
            _write_static_parts(archive, sheet_name)
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                _worksheet_xml(rows, columns),
            )
        return output.getvalue()


class XlsxStreamingReportWriter(StreamingReportWriter):
    async def write(
        self,
        row_batches: ReportRowBatches,
        columns: list[str],
        sheet_name: str,
    ) -> AsyncIterator[bytes]:
        if not columns:
            raise ValueError("XLSX report requires at least one column")

        descriptor, raw_path = tempfile.mkstemp(prefix="hostgator-report-", suffix=".xlsx")
        os.close(descriptor)
        path = Path(raw_path)
        try:
            with zipfile.ZipFile(
                path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                _write_static_parts(archive, sheet_name)
                with archive.open("xl/worksheets/sheet1.xml", mode="w") as worksheet:
                    worksheet.write(_worksheet_opening().encode("utf-8"))
                    worksheet.write(_row_xml(1, {column: column for column in columns}, columns).encode("utf-8"))
                    row_number = 2
                    async for rows in row_batches:
                        for row in rows:
                            worksheet.write(
                                _row_xml(row_number, row, columns).encode("utf-8")
                            )
                            row_number += 1
                    worksheet.write(_worksheet_closing(columns).encode("utf-8"))
        except BaseException:
            path.unlink(missing_ok=True)
            raise

        return _stream_temporary_file(path)


def _write_static_parts(archive: zipfile.ZipFile, sheet_name: str) -> None:
    archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
    archive.writestr("_rels/.rels", _ROOT_RELATIONSHIPS)
    archive.writestr("xl/workbook.xml", _workbook_xml(sheet_name))
    archive.writestr(
        "xl/_rels/workbook.xml.rels",
        _WORKBOOK_RELATIONSHIPS,
    )


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


def _worksheet_opening() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
    )


def _worksheet_closing(columns: list[str]) -> str:
    last_column = _column_name(len(columns))
    return f'</sheetData><autoFilter ref="A1:{last_column}1"/></worksheet>'


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
    return f'{_worksheet_opening()}{"".join(xml_rows)}{_worksheet_closing(columns)}'


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


async def _stream_temporary_file(
    path: Path,
    chunk_size: int = 64 * 1024,
) -> AsyncIterator[bytes]:
    try:
        with path.open("rb") as source:
            while True:
                chunk = await asyncio.to_thread(source.read, chunk_size)
                if not chunk:
                    return
                yield chunk
    finally:
        await asyncio.to_thread(path.unlink, True)
