import pytest

from src.application.contracts.unit_of_work import UnitOfWork
from src.infra.database.transactional_handler import TransactionalHandler


pytestmark = pytest.mark.unit


class RecordingUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> "RecordingUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()


@pytest.mark.asyncio
async def test_transactional_handler_returns_value_and_commits() -> None:
    unit_of_work = RecordingUnitOfWork()

    async def handler(value: int) -> int:
        return value * 2

    result = await TransactionalHandler(unit_of_work, handler)(21)

    assert result == 42
    assert unit_of_work.committed is True
    assert unit_of_work.rolled_back is False


@pytest.mark.asyncio
async def test_transactional_handler_propagates_error_and_rolls_back() -> None:
    unit_of_work = RecordingUnitOfWork()

    async def handler(_: int) -> int:
        raise RuntimeError("handler failed")

    with pytest.raises(RuntimeError, match="handler failed"):
        await TransactionalHandler(unit_of_work, handler)(21)

    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True
