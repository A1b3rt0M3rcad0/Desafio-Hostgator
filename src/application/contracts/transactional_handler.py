from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar


InputT = TypeVar("InputT", contravariant=True)
OutputT = TypeVar("OutputT", covariant=True)

Handler = Callable[[InputT], Awaitable[OutputT]]


class TransactionalHandlerContract(Protocol[InputT, OutputT]):

    async def __call__(self, input_data: InputT) -> OutputT:
        ...
