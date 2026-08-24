from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from data.synthetic.dataset_generator import create_synthetic_dataset
from risk_manager.decision import DecisionEngine
from risk_manager.features import FeatureEngine
from risk_manager.verification import VerificationService


@dataclass
class DummyDetectorResult:
    case_type: str
    confidence: float
    probabilities: dict[str, float]
    model_version: str = "detector-test-1.0"
    timestamp: str = "2026-08-24T00:00:00+00:00"


def _build_engine_and_data():
    customers, orders, txns, returns, chargebacks, devices, addresses = create_synthetic_dataset()
    feature_engine = FeatureEngine(
        transactions=txns,
        orders=orders,
        returns=returns,
        chargebacks=chargebacks,
        customers=customers,
        devices=devices,
        addresses=addresses,
        prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
    )
    verifier_service = VerificationService(feature_engine=feature_engine)
    decision_engine = DecisionEngine.from_policy_file("config/merchant_policies.json")
    return txns, verifier_service, decision_engine


def test_policy_registry_loads_and_resolves_default():
    engine = DecisionEngine.from_policy_file("config/merchant_policies.json")
    policy = engine.policy_registry.resolve_policy("unknown_merchant")
    assert policy.name == "standard"
    assert policy.costs.false_negative_cost > policy.costs.false_positive_cost


def test_decision_returns_expected_contract_fields():
    txns, verifier_service, decision_engine = _build_engine_and_data()
    verifier_result = verifier_service.verify("transaction_fraud", txns[2], detector_confidence=0.75)

    detector = DummyDetectorResult(
        case_type="transaction_fraud",
        confidence=0.75,
        probabilities={
            "return_abuse": 0.05,
            "transaction_fraud": 0.75,
            "fraud_spike": 0.10,
            "abuse_ring": 0.05,
            "normal": 0.05,
        },
    )

    decision = decision_engine.decide("merchant_a", detector, verifier_result)

    assert decision.decision in {"APPROVE", "MANUAL_REVIEW", "DEFENSIVE_ACTION"}
    assert 0.0 <= decision.risk_score <= 1.0
    assert 0.0 <= decision.confidence <= 1.0
    assert "APPROVE" in decision.expected_loss_by_action
    assert "MANUAL_REVIEW" in decision.expected_loss_by_action
    assert "DEFENSIVE_ACTION" in decision.expected_loss_by_action
    assert len(decision.rationale) >= 3


def test_high_risk_with_high_confidence_can_choose_defensive_action():
    txns, verifier_service, decision_engine = _build_engine_and_data()
    verifier_result = verifier_service.verify("fraud_spike", txns[2], detector_confidence=0.95)
    verifier_result.risk_score = 0.97
    verifier_result.confidence = 0.92
    verifier_result.verification_status = "VERIFIED_SUSPICIOUS"
    verifier_result.edge_flags = []

    detector = DummyDetectorResult(
        case_type="fraud_spike",
        confidence=0.96,
        probabilities={
            "return_abuse": 0.01,
            "transaction_fraud": 0.02,
            "fraud_spike": 0.95,
            "abuse_ring": 0.01,
            "normal": 0.01,
        },
    )

    decision = decision_engine.decide("merchant_b", detector, verifier_result)
    assert decision.decision in {"DEFENSIVE_ACTION", "MANUAL_REVIEW"}
    assert decision.expected_loss_by_action[decision.decision] <= max(decision.expected_loss_by_action.values())


def test_uncertainty_defaults_to_manual_review():
    txns, verifier_service, decision_engine = _build_engine_and_data()
    verifier_result = verifier_service.verify("transaction_fraud", txns[2], detector_confidence=0.35)
    verifier_result.risk_score = 0.50
    verifier_result.confidence = 0.42
    verifier_result.edge_flags = ["new_entity_low_history"]

    detector = DummyDetectorResult(
        case_type="transaction_fraud",
        confidence=0.40,
        probabilities={
            "return_abuse": 0.15,
            "transaction_fraud": 0.45,
            "fraud_spike": 0.10,
            "abuse_ring": 0.05,
            "normal": 0.25,
        },
    )

    decision = decision_engine.decide("merchant_a", detector, verifier_result)
    assert decision.decision == "MANUAL_REVIEW"


def test_expected_loss_math_for_approve_is_fn_weighted():
    txns, verifier_service, decision_engine = _build_engine_and_data()
    verifier_result = verifier_service.verify("return_abuse", txns[2], detector_confidence=0.65)
    verifier_result.risk_score = 0.20
    verifier_result.confidence = 0.90
    verifier_result.edge_flags = []
    verifier_result.verification_status = "VERIFIED_NOT_SUSPICIOUS"

    detector = DummyDetectorResult(
        case_type="return_abuse",
        confidence=0.30,
        probabilities={
            "return_abuse": 0.30,
            "transaction_fraud": 0.10,
            "fraud_spike": 0.05,
            "abuse_ring": 0.05,
            "normal": 0.50,
        },
    )

    decision = decision_engine.decide("merchant_a", detector, verifier_result)
    expected_approve = decision.risk_score * 200.0
    assert abs(decision.expected_loss_by_action["APPROVE"] - round(expected_approve, 6)) < 1e-6


def test_integration_detector_verifier_decision_flow():
    txns, verifier_service, decision_engine = _build_engine_and_data()

    detector = DummyDetectorResult(
        case_type="abuse_ring",
        confidence=0.73,
        probabilities={
            "return_abuse": 0.06,
            "transaction_fraud": 0.08,
            "fraud_spike": 0.05,
            "abuse_ring": 0.73,
            "normal": 0.08,
        },
    )
    verifier_result = verifier_service.verify("abuse_ring", txns[0], detector_confidence=detector.confidence)

    decision = decision_engine.decide("merchant_c", detector, verifier_result)

    assert decision.merchant_id == "merchant_c"
    assert decision.policy_name == "balanced"
    assert decision.model_versions["detector_model_version"] == "detector-test-1.0"
    assert decision.rule_versions["verifier_rule_version"] == verifier_result.rule_version
    assert len(decision.rationale) >= 4


def test_configurable_weights_via_engine():
    txns, verifier_service, _ = _build_engine_and_data()
    # Instantiate engine with custom weights: 80% detector, 20% verifier
    custom_engine = DecisionEngine.from_policy_file(
        "config/merchant_policies.json",
        detector_weight=0.80,
        verifier_weight=0.20,
    )

    verifier_result = verifier_service.verify("transaction_fraud", txns[2], detector_confidence=0.90)
    verifier_result.risk_score = 0.40
    verifier_result.confidence = 0.85
    verifier_result.edge_flags = []

    detector = DummyDetectorResult(
        case_type="transaction_fraud",
        confidence=0.90,
        probabilities={
            "transaction_fraud": 0.90,
            "normal": 0.10,
        },
    )

    decision = custom_engine.decide("merchant_a", detector, verifier_result)
    detector_signal = custom_engine._detector_risk_signal(
        detector.case_type, detector.probabilities, detector.confidence
    )
    expected_combined_risk = 0.80 * detector_signal + 0.20 * verifier_result.risk_score

    assert abs(decision.risk_score - round(expected_combined_risk, 4)) < 1e-4
    assert decision.combined_evidence["detector_weight"] == 0.80
    assert decision.combined_evidence["verifier_weight"] == 0.20
    assert "0.8*detector_signal + 0.2*verifier_risk" in decision.combined_evidence["combined_risk_formula"]


def test_case_type_specific_fp_fn_costs():
    txns, verifier_service, decision_engine = _build_engine_and_data()

    # Merchant B uses strict policy which defines case_costs for abuse_ring (FN=500, FP=60)
    detector_abuse = DummyDetectorResult(
        case_type="abuse_ring",
        confidence=0.80,
        probabilities={"abuse_ring": 0.80, "normal": 0.20},
    )
    verifier_abuse = verifier_service.verify("abuse_ring", txns[0], detector_confidence=0.80)
    verifier_abuse.risk_score = 0.50
    verifier_abuse.confidence = 0.80
    verifier_abuse.edge_flags = []

    decision_abuse = decision_engine.decide("merchant_b", detector_abuse, verifier_abuse)
    # Expected approve loss uses the case-specific FN cost of 500.0
    expected_abuse_approve = decision_abuse.risk_score * 500.0
    expected_abuse_defensive = (1.0 - decision_abuse.risk_score) * 60.0
    assert abs(decision_abuse.expected_loss_by_action["APPROVE"] - round(expected_abuse_approve, 6)) < 1e-6
    assert abs(decision_abuse.expected_loss_by_action["DEFENSIVE_ACTION"] - round(expected_abuse_defensive, 6)) < 1e-6

    # For a case type without override in strict policy (e.g. fraud_spike), baseline costs are used (FN=260, FP=30)
    detector_spike = DummyDetectorResult(
        case_type="fraud_spike",
        confidence=0.80,
        probabilities={"fraud_spike": 0.80, "normal": 0.20},
    )
    verifier_spike = verifier_service.verify("fraud_spike", txns[0], detector_confidence=0.80)
    verifier_spike.risk_score = 0.50
    verifier_spike.confidence = 0.80
    verifier_spike.edge_flags = []

    decision_spike = decision_engine.decide("merchant_b", detector_spike, verifier_spike)
    expected_spike_approve = decision_spike.risk_score * 260.0
    expected_spike_defensive = (1.0 - decision_spike.risk_score) * 30.0
    assert abs(decision_spike.expected_loss_by_action["APPROVE"] - round(expected_spike_approve, 6)) < 1e-6
    assert abs(decision_spike.expected_loss_by_action["DEFENSIVE_ACTION"] - round(expected_spike_defensive, 6)) < 1e-6


def test_decision_costs_case_type_lookup_helper():
    policy = DecisionEngine.from_policy_file("config/merchant_policies.json").policy_registry.resolve_policy("merchant_b")
    # Base costs
    assert policy.costs.false_negative_cost == 260.0
    assert policy.costs.false_positive_cost == 30.0

    # Overridden costs for abuse_ring
    abuse_costs = policy.costs.for_case_type("abuse_ring")
    assert abuse_costs.false_negative_cost == 500.0
    assert abuse_costs.false_positive_cost == 60.0
    assert policy.costs.get_false_negative_cost("abuse_ring") == 500.0
    assert policy.costs.get_false_positive_cost("abuse_ring") == 60.0

    # Non-overridden fallback
    normal_costs = policy.costs.for_case_type("normal")
    assert normal_costs.false_negative_cost == 260.0
    assert normal_costs.false_positive_cost == 30.0
    assert policy.costs.get_false_negative_cost(None) == 260.0

