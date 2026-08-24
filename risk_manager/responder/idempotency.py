from __future__ import annotations

import threading
from typing import Optional

from risk_manager.responder.types import ResponseResult


class IdempotencyStore:
    """Thread-safe in-memory idempotency store to prevent duplicate event execution."""

    def __init__(self, max_entries: int = 10_000):
        self._store: dict[str, ResponseResult] = {}
        self._lock = threading.Lock()
        self._max_entries = max_entries

    @staticmethod
    def make_key(merchant_id: str, event_id: str) -> str:
        return f"{merchant_id}::{event_id}"

    def get(self, merchant_id: str, event_id: str) -> Optional[ResponseResult]:
        key = self.make_key(merchant_id, event_id)
        with self._lock:
            return self._store.get(key)

    def set(self, merchant_id: str, event_id: str, result: ResponseResult) -> None:
        key = self.make_key(merchant_id, event_id)
        with self._lock:
            if len(self._store) >= self._max_entries:
                # Evict oldest entry (FIFO)
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]
            self._store[key] = result

    def contains(self, merchant_id: str, event_id: str) -> bool:
        key = self.make_key(merchant_id, event_id)
        with self._lock:
            return key in self._store

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
