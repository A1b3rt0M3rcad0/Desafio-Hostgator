from abc import ABC, abstractmethod
from src.presentation.http.schemas.request import Request
from src.presentation.http.schemas.response import Response

class Controller(ABC):

    @abstractmethod
    def handle(self, request: Request) -> Response:...