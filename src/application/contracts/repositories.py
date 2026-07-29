from abc import ABC, abstractmethod
from uuid import UUID
from typing import TypeVar, Generic

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