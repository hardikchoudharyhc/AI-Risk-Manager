from datetime import datetime, timezone
from decimal import Decimal

import pytest

from data.synthetic.dataset_generator import create_synthetic_dataset
from risk_manager.features import FeatureEngine
from risk_manager.models import Transaction
from risk_manager.verification import VerificationService


@pytest.fixture
def engine_and_transactions():
    customers, orders, txns, returns, chargebacks, devices, addresses = create_synthetic_dataset()
    engine = FeatureEngine(
        transactions=txns,
        orders=orders,
        returns=returns,
        chargebacks=chargebacks,
        customers=customers,
        devices=devices,
        addresses=addresses,
        prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
    )
    return engine, txns


def _assert_common_result_contract(result):
    assert result.verification_status in {
        "VERIFIED_SUSPICIOUS",
        "VERIFIED_NOT_SUSPICIOUS",
        "INCONCLUSIVE",
    }
    assert 0.0 <= result.risk_score <= 1.0
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.reasons, list)
    assert len(result.applicable_rules) >= 1
    assert result.model_version
    assert result.rule_version
    assert result.explanation.method in {"shap", "model_coefficients", "unavailable"}
    assert isinstance(result.evidence, dict)
    assert isinstance(result.historical_evidence, dict)


def test_return_abuse_verifier_contract(engine_and_transactions):
    engine, txns = engine_and_transactions
    service = VerificationService(feature_engine=engine)

    result = service.verify("return_abuse", txns[2], detector_confidence=0.67)

    _assert_common_result_contract(result)
    assert result.case_type == "return_abuse"
    assert result.verifier_name == "ReturnAbuseVerifier"


def test_transaction_fraud_verifier_contract(engine_and_transactions):
    engine, txns = engine_and_transactions
    service = VerificationService(feature_engine=engine)

    result = service.verify("transaction_fraud", txns[2], detector_confidence=0.60)

    _assert_common_result_contract(result)
    assert result.case_type == "transaction_fraud"
    assert result.verifier_name == "TransactionFraudVerifier"


def test_fraud_spike_verifier_contract(engine_and_transactions):
    engine, txns = engine_and_transactions
    service = VerificationService(feature_engine=engine)

    result = service.verify("fraud_spike", txns[2], detector_confidence=0.72)

    _assert_common_result_contract(result)
    assert result.case_type == "fraud_spike"
    assert result.verifier_name == "FraudSpikeVerifier"


def test_abuse_ring_verifier_contract(engine_and_transactions):
    engine, txns = engine_and_transactions
    service = VerificationService(feature_engine=engine)

    result = service.verify("abuse_ring", txns[0], detector_confidence=0.59)

    _assert_common_result_contract(result)
    assert result.case_type == "abuse_ring"
    assert result.verifier_name == "AbuseRingVerifier"


def test_missing_new_entity_handled_gracefully(engine_and_transactions):
    engine, txns = engine_and_transactions
    service = VerificationService(feature_engine=engine)

    new_txn = Transaction(
        transaction_id="TXN-NEW-LOW-HISTORY",
        order_id="ORD-NEW-LOW-HISTORY",
        customer_id="C-NEW",
        amount=Decimal("120.00"),
        currency="USD",
        payment_method="CARD",
        transaction_status="PENDING",
        timestamp=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
    )

    result = service.verify("transaction_fraud", new_txn, detector_confidence=0.40)

    _assert_common_result_contract(result)
    assert "new_entity_low_history" in result.edge_flags
    assert "missing_customer" in result.edge_flags
    assert result.confidence <= 0.85


def test_supports_detector_prediction_like_object(engine_and_transactions):
    engine, txns = engine_and_transactions
    service = VerificationService(feature_engine=engine)

    class DummyDetectorPrediction:
        case_type = "return_abuse"
        confidence = 0.73

    result = service.verify_from_detector_prediction(DummyDetectorPrediction(), txns[2])

    _assert_common_result_contract(result)
    assert result.case_type == "return_abuse"


def test_invalid_case_type_raises(engine_and_transactions):
    engine, txns = engine_and_transactions
    service = VerificationService(feature_engine=engine)

    with pytest.raises(ValueError):
        service.verify("normal", txns[0])


def test_explanation_payload_contains_top_features(engine_and_transactions):
    engine, txns = engine_and_transactions
    service = VerificationService(feature_engine=engine)

    result = service.verify("abuse_ring", txns[0], detector_confidence=0.55)

    _assert_common_result_contract(result)
    assert isinstance(result.explanation.top_features, list)
    assert len(result.explanation.top_features) >= 1
    assert "feature" in result.explanation.top_features[0]
