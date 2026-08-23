from typing import Any, Callable

from .base import Connector


class SimulatedApiConnector(Connector):
    """Adapter for a local callable that behaves like a REST response."""

    def __init__(self, fetch: Callable[[], list[dict[str, Any]]]):
        self.fetch = fetch

    def read(self) -> list[dict[str, Any]]:
        records = self.fetch()
        if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
            raise ValueError("Simulated API must return a list of objects")
        return records