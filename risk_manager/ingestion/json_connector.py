import json
from pathlib import Path
from typing import Any

from .base import Connector


class JsonConnector(Connector):
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def read(self) -> list[dict[str, Any]]:
        with self.path.open(encoding="utf-8") as source:
            payload = json.load(source)
        if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
            raise ValueError("JSON input must be a list of objects")
        return payload