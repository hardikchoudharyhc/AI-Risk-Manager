from datetime import datetime, timezone
import pytest

from data.synthetic.dataset_generator import create_synthetic_dataset
from risk_manager.decision import DecisionEngine, DecisionResult
from risk_manager.features import FeatureEngine
from risk_manager.responder import (
    AutoResponder,
    TemplateRegistry,
    IdempotencyStore,
    AuditLogger,
    ResponseResult,
)
from dataclasses import dataclass
from risk_manager.verification import VerificationService


@dataclass
class DummyDetectorResult:
    case_type: str
    confidence: float
    probabilities: dict[str, float]
    model_version: str = "detector-test-1.0"
    timestamp: str = "2026-08-24T00:00:00+00:00"


def _create_mock_decision_result(
    merchant_id: str = "merchant_a",
    decision: str = "MANUAL_REVIEW",
    case_type: str = "transaction_fraud",
    risk_score: float = 0.55,
    confidence: float = 0.70,
) -> DecisionResult:
    return DecisionResult(
        merchant_id=merchant_id,
        policy_name="standard",
        decision=decision,
        risk_score=risk_score,
        confidence=confidence,
        expected_loss_by_action={"APPROVE": 110.0, "MANUAL_REVIEW": 45.0, "DEFENSIVE_ACTION": 90.0},
        selected_expected_loss=45.0,
        rationale=["Combined risk score=0.55", "Chosen action: MANUAL_REVIEW"],
        detector_evidence={"case_type": case_type, "confidence": confidence, "probabilities": {case_type: confidence}},
        verifier_evidence={"case_type": case_type, "verification_status": "INCONCLUSIVE", "risk_score": risk_score, "reasons": ["Unusual velocity"]},
        combined_evidence={"combined_risk_formula": "0.35*detector_signal + 0.65*verifier_risk"},
        model_versions={"detector_model_version": "detector-1.0", "verifier_model_version": "verifier-1.0"},
        rule_versions={"verifier_rule_version": "rule-1.0"},
        policy_version="1.0.0",
        timestamp=DecisionResult.now_iso(),
    )


def test_template_registry_default_and_fallback():
    registry = TemplateRegistry.from_file("config/response_templates.json")

    # Known combinations
    action_ra = registry.resolve_action("MANUAL_REVIEW", "return_abuse")
    assert action_ra.action_code == "FLAG_RETURN_FOR_STAFF_REVIEW"
    assert action_ra.action_type == "QUEUE_MANUAL_REVIEW"

    # Approval
    action_app = registry.resolve_action("APPROVE", "transaction_fraud")
    assert action_app.action_code == "STANDARD_APPROVAL"
    assert action_app.instructions["allow_fulfillment"] is True

    # Unknown case type fallback
    action_unknown = registry.resolve_action("MANUAL_REVIEW", "unseen_future_risk")
    assert action_unknown.action_code == "GENERAL_MANUAL_REVIEW"

    # Unknown decision fallback
    action_invalid_dec = registry.resolve_action("INVALID_DECISION", "transaction_fraud")
    assert action_invalid_dec.action_type == "QUEUE_MANUAL_REVIEW"


def test_responder_routes_all_four_risk_classes_under_defensive_action():
    responder = AutoResponder.from_config("config/response_templates.json")

    expected_codes = {
        "return_abuse": "SUSPEND_RETURN_PRIVILEGES",
        "transaction_fraud": "DECLINE_AND_NOTIFY",
        "fraud_spike": "THROTTLE_VELOCITY_AND_ALERT_SECURITY",
        "abuse_ring": "QUARANTINE_LINKED_ENTITIES",
    }

    for case_type, expected_code in expected_codes.items():
        decision_res = _create_mock_decision_result(
            decision="DEFENSIVE_ACTION",
            case_type=case_type,
            risk_score=0.88,
        )
        resp = responder.respond(decision_res, event_id=f"evt_{case_type}")
        assert resp.action.action_code == expected_code
        assert resp.action.action_type == "DEFENSIVE_CONTROL"
        assert resp.is_duplicate is False


def test_responder_routes_all_four_risk_classes_under_manual_review():
    responder = AutoResponder.from_config("config/response_templates.json")

    expected_codes = {
        "return_abuse": "FLAG_RETURN_FOR_STAFF_REVIEW",
        "transaction_fraud": "STEP_UP_AUTHENTICATION_AND_REVIEW",
        "fraud_spike": "ALERT_OPS_TEAM_FOR_REVIEW",
        "abuse_ring": "INVESTIGATION_CASE_QUEUE",
    }

    for case_type, expected_code in expected_codes.items():
        decision_res = _create_mock_decision_result(
            decision="MANUAL_REVIEW",
            case_type=case_type,
            risk_score=0.60,
        )
        resp = responder.respond(decision_res, event_id=f"evt_mr_{case_type}")
        assert resp.action.action_code == expected_code
        assert resp.is_duplicate is False


def test_idempotency_prevents_duplicate_execution():
    responder = AutoResponder.from_config("config/response_templates.json")
    decision_res = _create_mock_decision_result(merchant_id="merchant_a", decision="DEFENSIVE_ACTION", case_type="transaction_fraud")

    # First call: fresh execution
    first_resp = responder.respond(decision_res, event_id="tx_12345")
    assert first_resp.is_duplicate is False
    assert first_resp.response_id.startswith("resp_")

    # Second call with same merchant and event ID: idempotent replay
    second_resp = responder.respond(decision_res, event_id="tx_12345")
    assert second_resp.is_duplicate is True
    assert second_resp.response_id == first_resp.response_id
    assert second_resp.action.action_code == first_resp.action.action_code

    # Different event ID: fresh execution
    third_resp = responder.respond(decision_res, event_id="tx_99999")
    assert third_resp.is_duplicate is False
    assert third_resp.response_id != first_resp.response_id


def test_audit_logger_records_and_overrides(tmp_path):
    log_file = tmp_path / "audit.jsonl"
    responder = AutoResponder.from_config("config/response_templates.json", log_file=log_file)

    decision_res = _create_mock_decision_result(merchant_id="merchant_b", decision="MANUAL_REVIEW", case_type="abuse_ring")
    resp = responder.respond(decision_res, event_id="evt_audit_001", input_source="test_runner")

    # Query audit record
    audit_records = responder.audit_logger.get_by_event_id("evt_audit_001")
    assert len(audit_records) == 1
    record = audit_records[0]

    assert record.audit_id == resp.audit_id
    assert record.merchant_id == "merchant_b"
    assert record.decision == "MANUAL_REVIEW"
    assert record.case_type == "abuse_ring"
    assert record.action_code == "INVESTIGATION_CASE_QUEUE"
    assert record.model_versions["detector_model_version"] == "detector-1.0"
    assert record.rule_versions["verifier_rule_version"] == "rule-1.0"
    assert record.policy_version == "1.0.0"
    assert record.input_source == "test_runner"

    # Human override recording
    override_ok = responder.audit_logger.record_human_override(
        audit_id=record.audit_id,
        reviewer_id="analyst_jane",
        override_decision="APPROVE",
        override_reason="Customer verified via video KYC",
    )
    assert override_ok is True
    assert record.human_override["reviewer_id"] == "analyst_jane"
    assert record.human_override["override_decision"] == "APPROVE"

    # Final outcome recording
    outcome_ok = responder.audit_logger.record_final_outcome(
        audit_id=record.audit_id,
        outcome="CONFIRMED_LEGITIMATE",
        chargeback_occurred=False,
    )
    assert outcome_ok is True
    assert record.final_outcome["outcome"] == "CONFIRMED_LEGITIMATE"

    # Verify JSONL log was written
    assert log_file.exists()
    content = log_file.read_text()
    assert "INVESTIGATION_CASE_QUEUE" in content


def test_safe_handling_of_edge_cases_and_missing_evidence():
    responder = AutoResponder.from_config("config/response_templates.json")

    # Decision result with empty / missing evidence
    minimal_res = DecisionResult(
        merchant_id="merchant_unknown",
        policy_name="standard",
        decision="DEFENSIVE_ACTION",
        risk_score=0.95,
        confidence=0.50,
        expected_loss_by_action={"APPROVE": 200.0, "MANUAL_REVIEW": 50.0, "DEFENSIVE_ACTION": 10.0},
        selected_expected_loss=10.0,
        rationale=[],
        detector_evidence={},
        verifier_evidence={},
        combined_evidence={},
        model_versions={},
        rule_versions={},
        policy_version="1.0.0",
        timestamp=DecisionResult.now_iso(),
    )

    resp = responder.respond(minimal_res, event_id="evt_empty_evidence")
    assert resp.decision == "DEFENSIVE_ACTION"
    assert resp.action.action_type == "DEFENSIVE_CONTROL"
    assert resp.case_type == "unknown"
    assert resp.action.action_code == "GENERIC_DEFENSIVE_HOLD"


def test_end_to_end_m1_through_m6_pipeline_integration():
    # 1. Dataset (M1)
    customers, orders, txns, returns, chargebacks, devices, addresses = create_synthetic_dataset()

    # 2. Features (M2)
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

    # 3. Verifier (M4)
    verifier_service = VerificationService(feature_engine=feature_engine)
    verifier_res = verifier_service.verify("transaction_fraud", txns[0], detector_confidence=0.85)

    # Mock Detector (M3)
    detector_res = DummyDetectorResult(
        case_type="transaction_fraud",
        confidence=0.85,
        probabilities={
            "return_abuse": 0.05,
            "transaction_fraud": 0.85,
            "fraud_spike": 0.05,
            "abuse_ring": 0.05,
        },
    )

    # 4. Decision Engine (M5)
    decision_engine = DecisionEngine.from_policy_file("config/merchant_policies.json")
    decision_res = decision_engine.decide("merchant_a", detector_res, verifier_res)

    # 5. Auto-Responder (M6)
    responder = AutoResponder.from_config("config/response_templates.json")
    response_res = responder.respond(decision_res, event_id=txns[0].transaction_id)

    # Verify contract
    assert response_res.merchant_id == "merchant_a"
    assert response_res.decision == decision_res.decision
    assert response_res.case_type == "transaction_fraud"
    assert response_res.action.action_code in {
        "STANDARD_APPROVAL",
        "STEP_UP_AUTHENTICATION_AND_REVIEW",
        "DECLINE_AND_NOTIFY",
    }
    assert response_res.is_duplicate is False

    # Verify audit trail
    records = responder.audit_logger.get_by_event_id(txns[0].transaction_id)
    assert len(records) == 1
    assert records[0].action_code == response_res.action.action_code
    assert records[0].risk_score == decision_res.risk_score
