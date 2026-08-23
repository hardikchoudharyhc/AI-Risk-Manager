import csv
from pathlib import Path
from typing import Any

from .base import Connector


class CsvConnector(Connector):
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def read(self) -> list[dict[str, Any]]:
        with self.path.open(newline="", encoding="utf-8") as source:
            return list(csv.DictReader(source))