from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from src.domain.objects import CursorPage
from src.domain.entities import UserEntity, CustomerEntity, TicketEntity, SatisfactionRatingEntity, TagEntity, TicketTagEntity
from uuid import UUID

T = TypeVar('T')

class Repository(ABC, Generic[T]):

    @abstractmethod
    async def add(self, entity:T) -> None:...

    @abstractmethod
    async def get(self, entity_id: UUID) -> T | None:...

    @abstractmethod
    async def update(self, entity:T) -> None:...

    @abstractmethod
    async def delete(self, entity_id: UUID) -> None:...

    @abstractmethod
    async def page(self, cursor: str | None, page_size: int = 20) -> CursorPage[T]:...


class UserRepository(Repository[UserEntity]): ...


class CustomerRepository(Repository[CustomerEntity]): ...


class TicketRepository(Repository[TicketEntity]): ...


class SatisfactionRatingRepository(Repository[SatisfactionRatingEntity]): ...


class TagRepository(Repository[TagEntity]): ...


class TicketTagRepository(Repository[TicketTagEntity]): ...