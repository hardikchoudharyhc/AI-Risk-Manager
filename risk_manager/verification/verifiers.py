from __future__ import annotations

from typing import Any

from risk_manager.verification.base import BaseVerifier
from risk_manager.verification.types import RuleEvaluation


class ReturnAbuseVerifier(BaseVerifier):
    def __init__(self, rule_version: str = "1.0.0", model_version: str = "ra-ml-1.0.0"):
        super().__init__(
            verifier_name="ReturnAbuseVerifier",
            case_type="return_abuse",
            rule_version=rule_version,
            model_version=model_version,
            ml_feature_names=[
                "customer_return_rate",
                "customer_return_count",
                "order_value_vs_avg_ratio",
                "recent_return_frequency",
                "customer_account_age_days",
            ],
            ml_feature_ranges={
                "customer_return_rate": (0.0, 1.0),
                "customer_return_count": (0.0, 100.0),
                "order_value_vs_avg_ratio": (0.0, 12.0),
                "recent_return_frequency": (0.0, 20.0),
                "customer_account_age_days": (0.0, 3650.0),
            },
            ml_feature_weights={
                "customer_return_rate": 0.35,
                "customer_return_count": 0.20,
                "order_value_vs_avg_ratio": 0.20,
                "recent_return_frequency": 0.15,
                "customer_account_age_days": -0.10,
            },
        )

    def _evaluate_rules(self, feature_map: dict[str, Any], history: dict[str, Any]) -> list[RuleEvaluation]:
        rr = float(feature_map.get("customer_return_rate", 0.0))
        rc = float(feature_map.get("customer_return_count", 0.0))
        ratio = float(feature_map.get("order_value_vs_avg_ratio", 0.0))
        freq = float(feature_map.get("recent_return_frequency", 0.0))

        return [
            RuleEvaluation(
                rule_id="RA-R1",
                description="High return rate",
                triggered=rr >= 0.45,
                weight=0.35,
                observed_value=rr,
                threshold=0.45,
                reason="Customer return rate exceeds expected baseline.",
            ),
            RuleEvaluation(
                rule_id="RA-R2",
                description="Repeated return behavior",
                triggered=rc >= 3,
                weight=0.25,
                observed_value=rc,
                threshold=3.0,
                reason="Customer has repeated historical returns.",
            ),
            RuleEvaluation(
                rule_id="RA-R3",
                description="Order value outlier vs history",
                triggered=ratio >= 2.5,
                weight=0.25,
                observed_value=ratio,
                threshold=2.5,
                reason="Current order value is unusually high relative to customer baseline.",
            ),
            RuleEvaluation(
                rule_id="RA-R4",
                description="Recent return burst",
                triggered=freq >= 2.0,
                weight=0.15,
                observed_value=freq,
                threshold=2.0,
                reason="Recent return frequency indicates potential return burst behavior.",
            ),
        ]

    def _historical_score(self, feature_map: dict[str, Any], history: dict[str, Any]) -> float:
        prior_orders = max(1.0, float(history.get("prior_order_count", 0)))
        prior_returns = float(history.get("prior_return_count", 0))
        return min(1.0, (prior_returns / prior_orders) * 1.4)


class TransactionFraudVerifier(BaseVerifier):
    def __init__(self, rule_version: str = "1.0.0", model_version: str = "tf-ml-1.0.0"):
        super().__init__(
            verifier_name="TransactionFraudVerifier",
            case_type="transaction_fraud",
            rule_version=rule_version,
            model_version=model_version,
            ml_feature_names=[
                "amount_vs_avg_ratio",
                "transaction_velocity_1h",
                "transaction_velocity_24h",
                "customer_failed_transaction_rate",
                "unusual_payment_method",
            ],
            ml_feature_ranges={
                "amount_vs_avg_ratio": (0.0, 12.0),
                "transaction_velocity_1h": (0.0, 10.0),
                "transaction_velocity_24h": (0.0, 5.0),
                "customer_failed_transaction_rate": (0.0, 1.0),
                "unusual_payment_method": (0.0, 1.0),
            },
            ml_feature_weights={
                "amount_vs_avg_ratio": 0.25,
                "transaction_velocity_1h": 0.25,
                "transaction_velocity_24h": 0.15,
                "customer_failed_transaction_rate": 0.30,
                "unusual_payment_method": 0.05,
            },
        )

    def _evaluate_rules(self, feature_map: dict[str, Any], history: dict[str, Any]) -> list[RuleEvaluation]:
        ratio = float(feature_map.get("amount_vs_avg_ratio", 0.0))
        velocity_1h = float(feature_map.get("transaction_velocity_1h", 0.0))
        failed_rate = float(feature_map.get("customer_failed_transaction_rate", 0.0))
        unusual_pm = 1.0 if bool(feature_map.get("unusual_payment_method", False)) else 0.0

        return [
            RuleEvaluation(
                rule_id="TF-R1",
                description="Amount anomaly",
                triggered=ratio >= 3.0,
                weight=0.30,
                observed_value=ratio,
                threshold=3.0,
                reason="Transaction amount is significantly above customer norm.",
            ),
            RuleEvaluation(
                rule_id="TF-R2",
                description="Burst activity",
                triggered=velocity_1h >= 1.5,
                weight=0.25,
                observed_value=velocity_1h,
                threshold=1.5,
                reason="Transaction burst in one-hour window is elevated.",
            ),
            RuleEvaluation(
                rule_id="TF-R3",
                description="Failed payment history",
                triggered=failed_rate >= 0.25,
                weight=0.30,
                observed_value=failed_rate,
                threshold=0.25,
                reason="Customer has elevated failed transaction rate.",
            ),
            RuleEvaluation(
                rule_id="TF-R4",
                description="Unusual payment method",
                triggered=unusual_pm >= 1.0,
                weight=0.15,
                observed_value=unusual_pm,
                threshold=1.0,
                reason="Payment method is unusual for this customer.",
            ),
        ]

    def _historical_score(self, feature_map: dict[str, Any], history: dict[str, Any]) -> float:
        prior_txn = max(1.0, float(history.get("prior_transaction_count", 0)))
        prior_cb = float(history.get("prior_chargeback_count", 0))
        return min(1.0, (prior_cb / prior_txn) * 3.0)


class FraudSpikeVerifier(BaseVerifier):
    def __init__(self, rule_version: str = "1.0.0", model_version: str = "fs-ml-1.0.0"):
        super().__init__(
            verifier_name="FraudSpikeVerifier",
            case_type="fraud_spike",
            rule_version=rule_version,
            model_version=model_version,
            ml_feature_names=[
                "current_transaction_rate_1h",
                "historical_transaction_rate_24h_avg",
                "transaction_rate_deviation",
                "fraud_rate_deviation",
                "spike_severity",
            ],
            ml_feature_ranges={
                "current_transaction_rate_1h": (0.0, 20.0),
                "historical_transaction_rate_24h_avg": (0.0, 2.0),
                "transaction_rate_deviation": (-1.0, 20.0),
                "fraud_rate_deviation": (-1.0, 20.0),
                "spike_severity": (0.0, 20.0),
            },
            ml_feature_weights={
                "current_transaction_rate_1h": 0.15,
                "historical_transaction_rate_24h_avg": -0.10,
                "transaction_rate_deviation": 0.25,
                "fraud_rate_deviation": 0.25,
                "spike_severity": 0.45,
            },
        )

    def _evaluate_rules(self, feature_map: dict[str, Any], history: dict[str, Any]) -> list[RuleEvaluation]:
        txn_dev = float(feature_map.get("transaction_rate_deviation", 0.0))
        fraud_dev = float(feature_map.get("fraud_rate_deviation", 0.0))
        severity = float(feature_map.get("spike_severity", 0.0))
        amt_z = abs(float(feature_map.get("amount_stddev_deviation", 0.0)))

        return [
            RuleEvaluation(
                rule_id="FS-R1",
                description="Transaction rate spike",
                triggered=txn_dev >= 1.5,
                weight=0.30,
                observed_value=txn_dev,
                threshold=1.5,
                reason="Recent transaction rate materially exceeds historical baseline.",
            ),
            RuleEvaluation(
                rule_id="FS-R2",
                description="Fraud signal spike",
                triggered=fraud_dev >= 1.0,
                weight=0.30,
                observed_value=fraud_dev,
                threshold=1.0,
                reason="Fraud-like outcomes are elevated versus baseline.",
            ),
            RuleEvaluation(
                rule_id="FS-R3",
                description="Overall spike severity",
                triggered=severity >= 1.25,
                weight=0.25,
                observed_value=severity,
                threshold=1.25,
                reason="Combined spike severity indicates material anomaly.",
            ),
            RuleEvaluation(
                rule_id="FS-R4",
                description="Amount distribution anomaly",
                triggered=amt_z >= 2.0,
                weight=0.15,
                observed_value=amt_z,
                threshold=2.0,
                reason="Transaction amount deviates strongly from recent distribution.",
            ),
        ]

    def _historical_score(self, feature_map: dict[str, Any], history: dict[str, Any]) -> float:
        prior_txn = float(history.get("prior_transaction_count", 0))
        if prior_txn < 5:
            return 0.3
        return min(1.0, abs(float(feature_map.get("spike_severity", 0.0))) / 3.0)


class AbuseRingVerifier(BaseVerifier):
    def __init__(self, rule_version: str = "1.0.0", model_version: str = "ar-ml-1.0.0"):
        super().__init__(
            verifier_name="AbuseRingVerifier",
            case_type="abuse_ring",
            rule_version=rule_version,
            model_version=model_version,
            ml_feature_names=[
                "accounts_per_device",
                "accounts_per_address",
                "devices_per_customer",
                "cluster_density",
                "shared_device_transactions",
            ],
            ml_feature_ranges={
                "accounts_per_device": (1.0, 15.0),
                "accounts_per_address": (1.0, 15.0),
                "devices_per_customer": (0.0, 10.0),
                "cluster_density": (0.0, 10.0),
                "shared_device_transactions": (0.0, 100.0),
            },
            ml_feature_weights={
                "accounts_per_device": 0.30,
                "accounts_per_address": 0.20,
                "devices_per_customer": 0.10,
                "cluster_density": 0.20,
                "shared_device_transactions": 0.20,
            },
        )

    def _evaluate_rules(self, feature_map: dict[str, Any], history: dict[str, Any]) -> list[RuleEvaluation]:
        accounts_per_device = float(feature_map.get("accounts_per_device", 0.0))
        accounts_per_address = float(feature_map.get("accounts_per_address", 0.0))
        cluster_density = float(feature_map.get("cluster_density", 0.0))
        shared_txns = float(feature_map.get("shared_device_transactions", 0.0))

        return [
            RuleEvaluation(
                rule_id="AR-R1",
                description="Many accounts share same device",
                triggered=accounts_per_device >= 3.0,
                weight=0.35,
                observed_value=accounts_per_device,
                threshold=3.0,
                reason="Device is linked to multiple accounts.",
            ),
            RuleEvaluation(
                rule_id="AR-R2",
                description="Many accounts share same address",
                triggered=accounts_per_address >= 3.0,
                weight=0.20,
                observed_value=accounts_per_address,
                threshold=3.0,
                reason="Address is linked to multiple accounts.",
            ),
            RuleEvaluation(
                rule_id="AR-R3",
                description="Dense suspicious cluster",
                triggered=cluster_density >= 1.5,
                weight=0.25,
                observed_value=cluster_density,
                threshold=1.5,
                reason="Entity graph density indicates coordinated behavior.",
            ),
            RuleEvaluation(
                rule_id="AR-R4",
                description="Cross-account shared device activity",
                triggered=shared_txns >= 5.0,
                weight=0.20,
                observed_value=shared_txns,
                threshold=5.0,
                reason="Cross-account transactions through shared devices are elevated.",
            ),
        ]

    def _historical_score(self, feature_map: dict[str, Any], history: dict[str, Any]) -> float:
        device_links = float(history.get("linked_device_count", 0))
        shared_txns = float(feature_map.get("shared_device_transactions", 0.0))
        if device_links <= 0:
            return 0.2
        return min(1.0, (shared_txns / max(1.0, device_links * 5.0)))
