from __future__ import annotations

import io
import zipfile
from collections.abc import AsyncIterator

import pytest

from src.application.contracts.reports import ReportRowBatch
from src.infra.reports.csv_writer import CsvStreamingReportWriter
from src.infra.reports.xlsx_writer import XlsxStreamingReportWriter


pytestmark = pytest.mark.unit


async def _batches() -> AsyncIterator[ReportRowBatch]:
    yield [
        {"id": 1, "name": "Cliente A"},
        {"id": 2, "name": "Cliente B"},
    ]
    yield [{"id": 3, "name": "Cliente C"}]


async def _collect(stream: AsyncIterator[bytes]) -> bytes:
    return b"".join([chunk async for chunk in stream])


@pytest.mark.asyncio
async def test_csv_streaming_writer_emits_header_and_all_batches() -> None:
    stream = await CsvStreamingReportWriter().write(
        _batches(),
        ["id", "name"],
        "Clientes",
    )

    content = (await _collect(stream)).decode("utf-8-sig")

    assert content.splitlines() == [
        "id,name",
        "1,Cliente A",
        "2,Cliente B",
        "3,Cliente C",
    ]


@pytest.mark.asyncio
async def test_xlsx_streaming_writer_builds_valid_workbook() -> None:
    stream = await XlsxStreamingReportWriter().write(
        _batches(),
        ["id", "name"],
        "Clientes",
    )
    content = await _collect(stream)

    with zipfile.ZipFile(io.BytesIO(content)) as workbook:
        names = set(workbook.namelist())
        worksheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")

    assert "xl/workbook.xml" in names
    assert worksheet.count("<row ") == 4
    assert "Cliente A" in worksheet
    assert "Cliente C" in worksheet
