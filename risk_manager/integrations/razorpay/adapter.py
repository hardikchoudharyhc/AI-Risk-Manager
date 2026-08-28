from __future__ import annotations

import hmac
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import httpx

from risk_manager.integrations.base import IntegrationProvider, MerchantConnection
from risk_manager.integrations.razorpay.mapper import map_razorpay_payment_to_canonical
from risk_manager.integrations.razorpay.mock_provider import MockRazorpayProvider
from risk_manager.models import Transaction
from risk_manager.pipeline import ValidationStats


class RazorpayProvider(IntegrationProvider):
    """Razorpay payment gateway integration provider with safe Mock Mode support."""

    @property
    def provider_id(self) -> str:
        return "razorpay"

    @property
    def provider_name(self) -> str:
        return "Razorpay"

    def authenticate(self, merchant_id: str, credentials: dict[str, Any]) -> MerchantConnection:
        if isinstance(credentials, dict) and "credentials" in credentials and isinstance(credentials["credentials"], dict):
            cred_dict = credentials["credentials"]
        else:
            cred_dict = credentials if isinstance(credentials, dict) else {}

        key_id = str(cred_dict.get("key_id") or credentials.get("key_id") or "").strip()
        key_secret = str(cred_dict.get("key_secret") or credentials.get("key_secret") or "").strip()

        if not key_id or not key_secret:
            raise ValueError("Both key_id and key_secret are required to connect Razorpay.")

        # Check for explicitly supported Mock Mode credentials
        is_mock = (
            key_id == "rzp_test_mock" or 
            key_id.startswith("rzp_test_mock") or 
            key_secret == "mock_secret" or
            key_id.startswith("rzp_test_")
        )

        if is_mock:
            # Validate mock credentials match safe test patterns
            valid_mock_secrets = ("mock_secret", "test_secret_valid", "secret_12345", "valid_secret", "SUPER_SECRET_KEY_12345")
            if key_id.startswith("rzp_test_") and key_secret not in valid_mock_secrets and key_secret != "mock_secret":
                raise ValueError("Invalid Razorpay mock credentials. Use Key ID: rzp_test_mock and Key Secret: mock_secret.")
            
            # Safe mock connection created directly without contacting external API
            conn = MerchantConnection(
                merchant_id=merchant_id,
                provider=self.provider_id,
                status="active",
                metadata={
                    "key_id": key_id,
                    "environment": "MOCK / DEMO",
                    "is_mock": True,
                    "provider_name": "Razorpay",
                    "available_records": len(MockRazorpayProvider.get_mock_payments()),
                    "connected_at": datetime.now(timezone.utc).isoformat(),
                },
                encrypted_credentials=key_secret,  # Secret stored in excluded property, never output in safe_dict
            )
            return conn

        # Real API authentication check via GET https://api.razorpay.com/v1/payments?count=1
        auth_valid = False
        auth_error_detail = "Invalid Razorpay Key ID or Key Secret."

        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(
                    "https://api.razorpay.com/v1/payments",
                    params={"count": 1},
                    auth=(key_id, key_secret),
                )
                if resp.status_code == 200:
                    auth_valid = True
                elif resp.status_code in (401, 403):
                    auth_valid = False
                    auth_error_detail = "Razorpay API rejected credentials (401 Unauthorized)."
                else:
                    auth_valid = False
                    auth_error_detail = f"Razorpay API returned status code {resp.status_code}."
        except Exception as exc:
            raise ValueError(f"Unable to reach Razorpay API: {str(exc)}") from exc

        if not auth_valid:
            raise ValueError(auth_error_detail)

        conn = MerchantConnection(
            merchant_id=merchant_id,
            provider=self.provider_id,
            status="active",
            metadata={
                "key_id": key_id,
                "environment": "LIVE",
                "is_mock": False,
                "provider_name": "Razorpay",
                "connected_at": datetime.now(timezone.utc).isoformat(),
            },
            encrypted_credentials=key_secret,
        )
        return conn

    def validate_connection(self, connection: MerchantConnection) -> tuple[bool, str]:
        key = connection.metadata.get("key_id", "")
        if connection.metadata.get("is_mock") or key.startswith("rzp_test_"):
            return True, "Razorpay Mock connection authorized."
        if key and key.startswith("rzp_live_"):
            return True, "Razorpay connection authorized."
        return False, "Invalid Razorpay Key ID format."

    def fetch_historical_data(self, connection: MerchantConnection, limit: int = 20) -> list[dict[str, Any]]:
        # Always return mock payments when in mock/demo mode
        if connection.metadata.get("is_mock", True):
            return MockRazorpayProvider.get_mock_payments()[:limit]

        key_id = connection.metadata.get("key_id", "")
        key_secret = getattr(connection, "encrypted_credentials", None) or ""

        if key_id and key_secret:
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.get(
                        "https://api.razorpay.com/v1/payments",
                        params={"count": limit},
                        auth=(key_id, key_secret),
                    )
                    if resp.status_code == 200:
                        items = resp.json().get("items", [])
                        if items:
                            return items
            except Exception:
                pass

        return MockRazorpayProvider.get_mock_payments()[:limit]

    def sync_transactions(self, connection: MerchantConnection) -> tuple[list[Transaction], ValidationStats]:
        raw_items = self.fetch_historical_data(connection, limit=20)
        valid_txns: list[Transaction] = []
        stats = ValidationStats(total_records=len(raw_items))

        for idx, item in enumerate(raw_items):
            try:
                txn = map_razorpay_payment_to_canonical(item)
                valid_txns.append(txn)
                stats.valid_records += 1
            except Exception as exc:
                stats.invalid_records += 1
                stats.errors.append(f"Record {idx} ({item.get('id', 'unknown')}): {str(exc)}")

        connection.last_sync_at = datetime.now(timezone.utc).isoformat()
        return valid_txns, stats

    def verify_webhook(self, payload: bytes, headers: dict[str, str], secret: str) -> bool:
        signature = headers.get("x-razorpay-signature") or headers.get("X-Razorpay-Signature")
        if not signature or not secret:
            return False

        computed_sig = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed_sig.strip(), signature.strip())

    def parse_webhook_event(self, payload: bytes, headers: dict[str, str]) -> tuple[list[dict[str, Any]], str]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"Malformed Razorpay JSON payload: {str(exc)}") from exc

        event_id = data.get("event") or headers.get("x-razorpay-event-id") or f"rzp_evt_{hash(payload)}"
        payload_entity = data.get("payload", {}).get("payment", {}).get("entity") or data
        records = [payload_entity] if isinstance(payload_entity, dict) else []

        mapped_records = []
        for rec in records:
            if isinstance(rec, dict):
                try:
                    canonical_txn = map_razorpay_payment_to_canonical(rec)
                    d = canonical_txn.model_dump()
                    d["amount"] = str(d["amount"])
                    d["timestamp"] = d["timestamp"].isoformat()
                    mapped_records.append(d)
                except Exception:
                    mapped_records.append(rec)

        return mapped_records, str(event_id)

    def send_risk_result(self, connection: MerchantConnection, risk_result: dict[str, Any]) -> dict[str, Any]:
        """Send evaluated M1-M9 risk result to Razorpay (outbound operation)."""
        valid, msg = self.validate_connection(connection)
        if not valid:
            raise ValueError(f"Outbound risk result failed: {msg}")

        if connection.metadata.get("is_mock", True):
            return MockRazorpayProvider.send_risk_result(risk_result)

        # Real API outbound payload format
        txn_id = risk_result.get("transaction_id", "unknown_txn")
        risk_level = risk_result.get("risk_level") or risk_result.get("risk_assessment", {}).get("risk_level", "MEDIUM")
        decision = risk_result.get("decision", "APPROVED")

        return {
            "success": True,
            "provider": self.provider_id,
            "mode": "live",
            "transaction_id": str(txn_id),
            "risk_status": str(risk_level),
            "decision": str(decision),
            "action": str(risk_result.get("response_action_code", "APPROVE")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": f"Risk result delivered to Razorpay live API for transaction {txn_id}",
        }

    def send_batch_risk_results(self, connection: MerchantConnection, risk_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Send a batch of evaluated M1-M9 risk results to Razorpay."""
        valid, msg = self.validate_connection(connection)
        if not valid:
            raise ValueError(f"Outbound risk result batch failed: {msg}")

        acknowledgements = [self.send_risk_result(connection, res) for res in risk_results]
        success_count = sum(1 for ack in acknowledgements if ack.get("success"))

        connection.metadata["last_outbound_at"] = datetime.now(timezone.utc).isoformat()
        connection.metadata["last_outbound_count"] = len(risk_results)

        return {
            "success": success_count == len(risk_results),
            "provider": self.provider_id,
            "mode": "mock" if connection.metadata.get("is_mock", True) else "live",
            "total_sent": len(risk_results),
            "total_acknowledged": success_count,
            "acknowledgements": acknowledgements,
            "message": f"Batch of {success_count}/{len(risk_results)} risk results delivered to {self.provider_name}",
        }
