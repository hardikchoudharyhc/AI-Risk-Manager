from abc import ABC, abstractmethod
from typing import Any


class Connector(ABC):
    @abstractmethod
    def read(self) -> list[dict[str, Any]]:
        """Read source records while preserving source-specific field names."""