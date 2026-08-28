from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field

from risk_manager.models import Transaction
from risk_manager.pipeline import ValidationStats


class MerchantConnection(BaseModel):
    model_config = ConfigDict(extra="ignore")

    connection_id: str = Field(default_factory=lambda: f"conn_{uuid.uuid4().hex[:12]}")
    merchant_id: str
    provider: str
    status: str = Field(default="active", description="active, inactive, pending, or error")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_sync_at: str | None = None
    last_event_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    encrypted_credentials: str | None = Field(default=None, exclude=True)

    def safe_dict(self) -> dict[str, Any]:
        """Return public dictionary representation without sensitive tokens or credentials."""
        d = self.model_dump()
        d.pop("encrypted_credentials", None)
        return d


class DeduplicationCache:
    """In-memory idempotency cache for webhook event deduplication."""

    def __init__(self, max_size: int = 10000):
        self._seen_events: set[str] = set()
        self._max_size = max_size

    def is_duplicate(self, event_id: str) -> bool:
        if not event_id:
            return False
        return event_id in self._seen_events

    def mark_seen(self, event_id: str) -> None:
        if not event_id:
            return
        if len(self._seen_events) >= self._max_size:
            # Clear half of the cache if capacity reached
            self._seen_events = set(list(self._seen_events)[self._max_size // 2:])
        self._seen_events.add(event_id)


class IntegrationProvider(ABC):
    """Abstract Base Class for all provider-agnostic e-commerce/payment integrations."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. 'shopify', 'razorpay', 'generic_api')."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name (e.g. 'Shopify', 'Razorpay', 'Generic API')."""
        pass

    @abstractmethod
    def authenticate(self, merchant_id: str, credentials: dict[str, Any]) -> MerchantConnection:
        """Authenticate/connect merchant credentials and return a connection instance."""
        pass

    @abstractmethod
    def validate_connection(self, connection: MerchantConnection) -> tuple[bool, str]:
        """Validate whether an active connection is authorized and healthy."""
        pass

    @abstractmethod
    def fetch_historical_data(self, connection: MerchantConnection, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch historical records from provider in raw or pre-mapped format."""
        pass

    @abstractmethod
    def sync_transactions(self, connection: MerchantConnection) -> tuple[list[Transaction], ValidationStats]:
        """Fetch and convert merchant records into canonical Transaction objects."""
        pass

    @abstractmethod
    def verify_webhook(self, payload: bytes, headers: dict[str, str], secret: str) -> bool:
        """Verify webhook signature or token authenticity."""
        pass

    @abstractmethod
    def parse_webhook_event(self, payload: bytes, headers: dict[str, str]) -> tuple[list[dict[str, Any]], str]:
        """Parse raw webhook bytes into raw record dictionaries and event ID."""
        pass

    def send_risk_result(self, connection: MerchantConnection, risk_result: dict[str, Any]) -> dict[str, Any]:
        """Send evaluated M1-M9 risk result back to provider (outbound operation)."""
        return {
            "success": True,
            "provider": self.provider_id,
            "mode": "mock" if connection.metadata.get("is_mock", True) else "live",
            "transaction_id": str(risk_result.get("transaction_id", "unknown")),
            "risk_status": str(risk_result.get("risk_level", "UNKNOWN")),
            "action": str(risk_result.get("decision", "APPROVED")),
            "message": f"Risk result received by provider {self.provider_name}",
        }

    def send_batch_risk_results(self, connection: MerchantConnection, risk_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Send a batch of evaluated M1-M9 risk results back to provider."""
        acknowledgements = [self.send_risk_result(connection, res) for res in risk_results]
        success_count = sum(1 for ack in acknowledgements if ack.get("success"))
        return {
            "success": success_count == len(risk_results),
            "provider": self.provider_id,
            "mode": "mock" if connection.metadata.get("is_mock", True) else "live",
            "total_sent": len(risk_results),
            "total_acknowledged": success_count,
            "acknowledgements": acknowledgements,
            "message": f"Batch of {success_count}/{len(risk_results)} risk results delivered to {self.provider_name}",
        }
