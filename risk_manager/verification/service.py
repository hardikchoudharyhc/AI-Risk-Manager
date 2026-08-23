from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from risk_manager.features.engine import FeatureEngine
from risk_manager.models import Transaction
from risk_manager.verification.types import VerificationResult
from risk_manager.verification.verifiers import (
    ReturnAbuseVerifier,
    TransactionFraudVerifier,
    FraudSpikeVerifier,
    AbuseRingVerifier,
)


@dataclass
class VerificationService:
    """Routes detector case type to class-specific verifier."""

    feature_engine: FeatureEngine
    rule_version: str = "1.0.0"

    def __post_init__(self):
        self._verifiers = {
            "return_abuse": ReturnAbuseVerifier(rule_version=self.rule_version),
            "transaction_fraud": TransactionFraudVerifier(rule_version=self.rule_version),
            "fraud_spike": FraudSpikeVerifier(rule_version=self.rule_version),
            "abuse_ring": AbuseRingVerifier(rule_version=self.rule_version),
        }

    def verify(
        self,
        case_type: str,
        transaction: Transaction,
        detector_confidence: float = 0.0,
    ) -> VerificationResult:
        if case_type not in self._verifiers:
            raise ValueError(f"Unsupported case type for verifier: {case_type}")

        history = self._build_history_snapshot(transaction)
        verifier = self._verifiers[case_type]

        if case_type == "return_abuse":
            features = self.feature_engine.extract_return_abuse_features(transaction)
        elif case_type == "transaction_fraud":
            features = self.feature_engine.extract_transaction_fraud_features(transaction)
        elif case_type == "fraud_spike":
            features = self.feature_engine.extract_fraud_spike_features(transaction)
        else:
            features = self.feature_engine.extract_abuse_ring_features(transaction)

        return verifier.verify(features, history, detector_confidence=detector_confidence)

    def verify_from_detector_prediction(
        self,
        detector_prediction,
        transaction: Transaction,
    ) -> VerificationResult:
        return self.verify(
            case_type=detector_prediction.case_type,
            transaction=transaction,
            detector_confidence=getattr(detector_prediction, "confidence", 0.0),
        )

    def _build_history_snapshot(self, transaction: Transaction) -> dict[str, Any]:
        ts: datetime = transaction.timestamp
        customer_id = transaction.customer_id

        orders = [
            order for order in self.feature_engine.orders.values()
            if order.customer_id == customer_id and order.timestamp < ts
        ]
        txns = [
            txn for txn in self.feature_engine.transactions.values()
            if txn.customer_id == customer_id and txn.timestamp < ts
        ]
        returns = [
            ret for ret in self.feature_engine.returns.values()
            if ret.customer_id == customer_id and ret.timestamp < ts
        ]
        chargebacks = [
            cb for cb in self.feature_engine.chargebacks.values()
            if cb.customer_id == customer_id and cb.timestamp < ts
        ]

        customer_devices = [
            d.device_id for d in self.feature_engine.devices.values()
            if d.customer_id == customer_id
        ]
        customer_addresses = [
            a.address_id for a in self.feature_engine.addresses.values()
            if a.customer_id == customer_id
        ]

        shared_device_transactions = 0
        if customer_devices:
            for txn in self.feature_engine.transactions.values():
                if txn.customer_id == customer_id:
                    continue
                other_devices = [
                    d.device_id for d in self.feature_engine.devices.values()
                    if d.customer_id == txn.customer_id
                ]
                if any(device in customer_devices for device in other_devices):
                    shared_device_transactions += 1

        edge_flags: list[str] = []
        if not orders and not txns:
            edge_flags.append("new_entity_low_history")
        if customer_id not in self.feature_engine.customers:
            edge_flags.append("missing_customer")
        if not customer_devices:
            edge_flags.append("missing_device_links")
        if not customer_addresses:
            edge_flags.append("missing_address_links")

        return {
            "prior_order_count": len(orders),
            "prior_transaction_count": len(txns),
            "prior_return_count": len(returns),
            "prior_chargeback_count": len(chargebacks),
            "linked_device_count": len(customer_devices),
            "linked_address_count": len(customer_addresses),
            "shared_device_transaction_count": shared_device_transactions,
            "missing_customer": customer_id not in self.feature_engine.customers,
            "new_or_low_history": len(txns) < 2,
            "edge_flags": edge_flags,
        }
