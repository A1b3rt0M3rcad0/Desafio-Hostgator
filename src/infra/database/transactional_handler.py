from typing import Generic, TypeVar

from src.application.contracts.transactional_handler import Handler
from src.application.contracts.unit_of_work import UnitOfWork


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class TransactionalHandler(Generic[InputT, OutputT]):

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        handler: Handler[InputT, OutputT],
    ) -> None:
        self._unit_of_work = unit_of_work
        self._handler = handler

    async def __call__(self, input_data: InputT) -> OutputT:
        async with self._unit_of_work:
            return await self._handler(input_data)
