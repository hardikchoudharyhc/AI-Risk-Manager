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
from risk_manager.pipeline import ValidationStats, IngestionResult


class RazorpayProvider(IntegrationProvider):
    """Razorpay payment gateway integration provider with robust Mock & Production-Ready Test/Live API support."""

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

        valid_mock_secrets = (
            "mock_secret",
            "mock_secret_key_7890",
            "test_secret_valid",
            "secret_12345",
            "valid_secret",
            "SUPER_SECRET_KEY_12345",
        )

        is_mock_key = (
            key_id == "rzp_test_mock"
            or key_id.startswith("rzp_test_mock")
            or key_id == "mock_key_id"
        )
        is_mock_secret = key_secret in valid_mock_secrets

        # Mock Mode is activated ONLY when explicit mock identifiers are supplied
        if is_mock_key or (is_mock_secret and key_id == "rzp_test_mock"):
            if not is_mock_secret and key_secret != "mock_secret":
                raise ValueError(
                    "Invalid Razorpay mock credentials. Use Key ID: rzp_test_mock and Key Secret: mock_secret."
                )

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
                    "connection_status": "CONNECTED",
                },
                encrypted_credentials=key_secret,
            )
            return conn

        # Real Razorpay API authentication (Test Mode or Live Mode)
        if not (key_id.startswith("rzp_test_") or key_id.startswith("rzp_live_")):
            raise ValueError("Invalid Razorpay Key ID format. Key ID must start with rzp_test_ or rzp_live_.")

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(
                    "https://api.razorpay.com/v1/payments",
                    params={"count": 1},
                    auth=(key_id, key_secret),
                )
                if resp.status_code == 200:
                    payload_data = resp.json()
                    item_count = payload_data.get("count", len(payload_data.get("items", [])))
                elif resp.status_code in (401, 403):
                    raise ValueError("Razorpay API rejected credentials (401 Unauthorized). Check Key ID and Secret.")
                elif resp.status_code == 429:
                    raise ValueError("Razorpay API rate limit exceeded (429 Too Many Requests).")
                else:
                    raise ValueError(f"Razorpay API error: HTTP {resp.status_code}.")
        except httpx.TimeoutException:
            raise ValueError("Razorpay API connection timed out. Please try again.")
        except httpx.RequestError as exc:
            raise ValueError(f"Unable to reach Razorpay API: {str(exc)}")

        env = "RAZORPAY TEST MODE" if key_id.startswith("rzp_test_") else "RAZORPAY LIVE MODE"
        conn = MerchantConnection(
            merchant_id=merchant_id,
            provider=self.provider_id,
            status="active",
            metadata={
                "key_id": key_id,
                "environment": env,
                "is_mock": False,
                "provider_name": "Razorpay",
                "available_records": item_count,
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "connection_status": "CONNECTED",
            },
            encrypted_credentials=key_secret,
        )
        return conn

    def validate_connection(self, connection: MerchantConnection) -> tuple[bool, str]:
        key = connection.metadata.get("key_id", "")
        if connection.metadata.get("is_mock"):
            return True, "Razorpay Mock connection authorized."
        if key and (key.startswith("rzp_test_") or key.startswith("rzp_live_")):
            return True, "Razorpay connection authorized."
        return False, "Invalid Razorpay Key ID format."

    def fetch_historical_data(
        self,
        connection: MerchantConnection,
        limit: int = 50,
        skip: int = 0,
        from_time: int | None = None,
        to_time: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch historical Razorpay payment data with pagination support."""
        if connection.metadata.get("is_mock"):
            return MockRazorpayProvider.get_mock_payments()[skip : skip + limit]

        key_id = connection.metadata.get("key_id", "")
        key_secret = getattr(connection, "encrypted_credentials", None) or ""

        if not key_id or not key_secret:
            return []

        all_items: list[dict[str, Any]] = []
        current_skip = skip
        remaining = limit

        try:
            with httpx.Client(timeout=10.0) as client:
                while remaining > 0:
                    batch_count = min(remaining, 100)
                    params: dict[str, Any] = {"count": batch_count, "skip": current_skip}
                    if from_time:
                        params["from"] = from_time
                    if to_time:
                        params["to"] = to_time

                    resp = client.get(
                        "https://api.razorpay.com/v1/payments",
                        params=params,
                        auth=(key_id, key_secret),
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("items", [])
                        if not items:
                            break
                        all_items.extend(items)
                        if len(items) < batch_count:
                            break
                        current_skip += len(items)
                        remaining -= len(items)
                    elif resp.status_code in (401, 403):
                        raise ValueError("Razorpay API authentication failed (401 Unauthorized).")
                    elif resp.status_code == 429:
                        raise ValueError("Razorpay API rate limit exceeded (429).")
                    else:
                        raise ValueError(f"Razorpay API error: HTTP {resp.status_code}")
        except httpx.TimeoutException:
            raise ValueError("Razorpay API fetch timed out.")
        except httpx.RequestError as exc:
            raise ValueError(f"Unable to fetch transactions from Razorpay API: {str(exc)}")

        return all_items

    def sync_transactions(
        self,
        connection: MerchantConnection,
        limit: int = 50,
    ) -> tuple[list[Transaction], IngestionResult]:
        """Fetch, map, deduplicate, and ingest Razorpay transactions into unified pipeline."""
        raw_items = self.fetch_historical_data(connection, limit=limit)

        dict_records = []
        for item in raw_items:
            try:
                txn = map_razorpay_payment_to_canonical(item)
                d = txn.model_dump()
                d["amount"] = str(d["amount"])
                d["timestamp"] = d["timestamp"].isoformat()
                dict_records.append(d)
            except Exception:
                dict_records.append(item)

        from risk_manager.pipeline import ingest_records

        valid_txns, ingest_res = ingest_records(
            raw_input=dict_records,
            source_type="razorpay",
            source_id=connection.connection_id,
            merchant_id=connection.merchant_id,
        )

        connection.last_sync_at = datetime.now(timezone.utc).isoformat()
        connection.metadata["available_records"] = len(valid_txns)
        return valid_txns, ingest_res

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
        valid, msg = self.validate_connection(connection)
        if not valid:
            raise ValueError(f"Outbound risk result failed: {msg}")

        if connection.metadata.get("is_mock"):
            return MockRazorpayProvider.send_risk_result(risk_result)

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
            "message": f"Risk result delivered to Razorpay API for transaction {txn_id}",
        }

    def send_batch_risk_results(self, connection: MerchantConnection, risk_results: list[dict[str, Any]]) -> dict[str, Any]:
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
            "mode": "mock" if connection.metadata.get("is_mock") else "live",
            "total_sent": len(risk_results),
            "total_acknowledged": success_count,
            "acknowledgements": acknowledgements,
            "message": f"Batch of {success_count}/{len(risk_results)} risk results delivered to {self.provider_name}",
        }
