from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from src.domain.objects import CursorPage
from uuid import UUID

T = TypeVar('T')

class Repository(ABC, Generic[T]):

    @abstractmethod
    def add(self, entity:T):...

    @abstractmethod
    def get(self, entity_id: UUID):...

    @abstractmethod
    def update(self, entity:T):...

    @abstractmethod
    def delete(self, entity_id: UUID):...

    @abstractmethod
    def page(self, cursor: str | None, page_size: int = 20) -> CursorPage[T]:...