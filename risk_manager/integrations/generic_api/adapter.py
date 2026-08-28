from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from risk_manager.integrations.base import IntegrationProvider, MerchantConnection
from risk_manager.models import Transaction
from risk_manager.pipeline import ingest_raw_data, ValidationStats


def validate_api_url(url: str) -> tuple[bool, str]:
    """
    Safely validate an external API URL to prevent SSRF, loopback, and local network access.
    """
    if not url or not isinstance(url, str):
        return False, "URL string is empty or invalid."
    
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return False, "URL protocol must be HTTP or HTTPS."

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False, "Invalid URL hostname."

    # Prevent loopback, private ranges, metadata service IPs
    forbidden_hosts = {
        "localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"
    }
    if hostname in forbidden_hosts or hostname.startswith("127.") or hostname.startswith("192.168.") or hostname.startswith("10."):
        return False, "Access to private, internal, or loopback network addresses is prohibited."

    return True, "URL is valid."


class GenericAPIProvider(IntegrationProvider):
    """Provider adapter for generic REST API transaction ingestion."""

    @property
    def provider_id(self) -> str:
        return "generic_api"

    @property
    def provider_name(self) -> str:
        return "Generic REST API"

    def authenticate(self, merchant_id: str, credentials: dict[str, Any]) -> MerchantConnection:
        api_endpoint = credentials.get("api_endpoint", "https://api.merchant.com/v1/transactions")
        valid, msg = validate_api_url(api_endpoint)
        if not valid:
            raise ValueError(f"Invalid API Endpoint: {msg}")

        conn = MerchantConnection(
            merchant_id=merchant_id,
            provider=self.provider_id,
            status="active",
            metadata={
                "api_endpoint": api_endpoint,
                "auth_type": credentials.get("auth_type", "api_key"),
                "header_name": credentials.get("header_name", "X-API-Key"),
            },
        )
        return conn

    def validate_connection(self, connection: MerchantConnection) -> tuple[bool, str]:
        endpoint = connection.metadata.get("api_endpoint", "")
        return validate_api_url(endpoint)

    def fetch_historical_data(self, connection: MerchantConnection, limit: int = 100) -> list[dict[str, Any]]:
        # Mock fetch returning canonical-compatible records for testing/foundation
        return [
            {
                "transaction_id": f"GEN-API-{i+100}",
                "order_id": f"ORD-GEN-{i+100}",
                "customer_id": f"C-GEN-{i+100}",
                "amount": str(100.0 + i * 15.0),
                "currency": "USD",
                "payment_method": "CARD",
                "transaction_status": "COMPLETED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for i in range(min(limit, 5))
        ]

    def sync_transactions(self, connection: MerchantConnection) -> tuple[list[Transaction], ValidationStats]:
        raw_items = self.fetch_historical_data(connection)
        valid_txns, stats, _, _ = ingest_raw_data(raw_items)
        connection.last_sync_at = datetime.now(timezone.utc).isoformat()
        return valid_txns, stats

    def verify_webhook(self, payload: bytes, headers: dict[str, str], secret: str) -> bool:
        # Standard token or header match verification interface
        auth_header = headers.get("x-webhook-secret") or headers.get("X-Webhook-Secret") or headers.get("authorization")
        if not auth_header:
            return False
        return auth_header.strip() == secret.strip()

    def parse_webhook_event(self, payload: bytes, headers: dict[str, str]) -> tuple[list[dict[str, Any]], str]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"Malformed JSON payload in webhook: {str(exc)}") from exc

        event_id = headers.get("x-event-id") or headers.get("X-Event-ID") or f"evt_{hash(payload)}"

        if isinstance(data, dict):
            records = [data]
        elif isinstance(data, list):
            records = data
        else:
            records = []

        return records, str(event_id)
