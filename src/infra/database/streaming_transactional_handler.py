from collections.abc import AsyncIterator
from typing import Any, Generic, TypeVar

from src.application.contracts.transactional_handler import Handler
from src.application.contracts.unit_of_work import UnitOfWork


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class StreamingTransactionalHandler(Generic[InputT, OutputT]):
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        handler: Handler[InputT, OutputT],
    ) -> None:
        self._unit_of_work = unit_of_work
        self._handler = handler

    async def __call__(self, input_data: InputT) -> OutputT:
        await self._unit_of_work.__aenter__()
        try:
            output = await self._handler(input_data)
        except BaseException as error:
            await self._unit_of_work.__aexit__(
                type(error),
                error,
                error.__traceback__,
            )
            raise

        source = getattr(output, "stream", None)
        if source is None:
            await self._unit_of_work.__aexit__(None, None, None)
            return output

        setattr(output, "stream", self._managed_stream(source))
        return output

    async def _managed_stream(self, source: Any) -> AsyncIterator[bytes]:
        error: BaseException | None = None
        try:
            async for chunk in source:
                yield bytes(chunk)
        except BaseException as caught:
            error = caught
            raise
        finally:
            await self._unit_of_work.__aexit__(
                type(error) if error is not None else None,
                error,
                error.__traceback__ if error is not None else None,
            )
