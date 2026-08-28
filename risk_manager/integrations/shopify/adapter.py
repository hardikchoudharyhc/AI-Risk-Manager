from __future__ import annotations

import base64
import hmac
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from risk_manager.integrations.base import IntegrationProvider, MerchantConnection
from risk_manager.models import Transaction
from risk_manager.pipeline import ingest_raw_data, ValidationStats


class ShopifyProvider(IntegrationProvider):
    """Shopify store integration provider interface/skeleton."""

    @property
    def provider_id(self) -> str:
        return "shopify"

    @property
    def provider_name(self) -> str:
        return "Shopify"

    def authenticate(self, merchant_id: str, credentials: dict[str, Any]) -> MerchantConnection:
        shop_domain = credentials.get("shop_domain", "merchant-store.myshopify.com")
        if not shop_domain.endswith(".myshopify.com"):
            shop_domain = f"{shop_domain.split('/')[0]}.myshopify.com"

        conn = MerchantConnection(
            merchant_id=merchant_id,
            provider=self.provider_id,
            status="active",
            metadata={
                "shop_domain": shop_domain,
                "scope": credentials.get("scope", "read_orders,read_customers"),
                "installed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return conn

    def validate_connection(self, connection: MerchantConnection) -> tuple[bool, str]:
        shop = connection.metadata.get("shop_domain", "")
        if shop and shop.endswith(".myshopify.com"):
            return True, "Shopify connection configured."
        return False, "Invalid Shopify domain."

    def fetch_historical_data(self, connection: MerchantConnection, limit: int = 100) -> list[dict[str, Any]]:
        # Foundation sample payload simulating Shopify orders webhook/REST payload
        return [
            {
                "id": 1001,
                "name": "#SHOP-1001",
                "customer": {"id": "C-SHOP-101"},
                "total_price": "180.00",
                "currency": "USD",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "financial_status": "paid",
                "payment_gateway_names": ["shopify_payments"],
            }
        ]

    def sync_transactions(self, connection: MerchantConnection) -> tuple[list[Transaction], ValidationStats]:
        raw_items = self.fetch_historical_data(connection)
        valid_txns, stats, _, _ = ingest_raw_data(raw_items)
        connection.last_sync_at = datetime.now(timezone.utc).isoformat()
        return valid_txns, stats

    def verify_webhook(self, payload: bytes, headers: dict[str, str], secret: str) -> bool:
        """Verify Shopify HMAC-SHA256 signature header (x-shopify-hmac-sha256)."""
        hmac_header = headers.get("x-shopify-hmac-sha256") or headers.get("X-Shopify-Hmac-SHA256")
        if not hmac_header or not secret:
            return False

        computed_hmac = base64.b64encode(
            hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
        ).decode("utf-8")

        return hmac.compare_digest(computed_hmac.strip(), hmac_header.strip())

    def parse_webhook_event(self, payload: bytes, headers: dict[str, str]) -> tuple[list[dict[str, Any]], str]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"Malformed Shopify JSON payload: {str(exc)}") from exc

        event_id = headers.get("x-shopify-webhook-id") or headers.get("X-Shopify-Webhook-Id") or f"shop_evt_{hash(payload)}"

        records = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
        return records, str(event_id)
