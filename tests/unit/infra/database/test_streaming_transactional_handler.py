from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Self

import pytest

from src.application.contracts.unit_of_work import UnitOfWork
from src.infra.database.streaming_transactional_handler import (
    StreamingTransactionalHandler,
)
from src.presentation.http.schemas.response import Response


pytestmark = pytest.mark.unit


class RecordingUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.entered = 0
        self.committed = False
        self.rolled_back = False
        self.exited = 0

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> Self:
        self.entered += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.exited += 1
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()


async def _collect(stream: AsyncIterator[bytes]) -> bytes:
    return b"".join([chunk async for chunk in stream])


@pytest.mark.asyncio
async def test_streaming_handler_closes_transaction_after_consumption() -> None:
    unit_of_work = RecordingUnitOfWork()

    async def source() -> AsyncIterator[bytes]:
        yield b"first"
        yield b"second"

    async def handler(_: int) -> Response:
        return Response(status_code=200, stream=source())

    output = await StreamingTransactionalHandler(unit_of_work, handler)(1)

    assert unit_of_work.entered == 1
    assert unit_of_work.exited == 0
    assert await _collect(output.stream) == b"firstsecond"
    assert unit_of_work.exited == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rolled_back is False


@pytest.mark.asyncio
async def test_streaming_handler_rolls_back_when_stream_fails() -> None:
    unit_of_work = RecordingUnitOfWork()

    async def source() -> AsyncIterator[bytes]:
        yield b"partial"
        raise RuntimeError("stream failed")

    async def handler(_: int) -> Response:
        return Response(status_code=200, stream=source())

    output = await StreamingTransactionalHandler(unit_of_work, handler)(1)

    with pytest.raises(RuntimeError, match="stream failed"):
        await _collect(output.stream)

    assert unit_of_work.exited == 1
    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True
