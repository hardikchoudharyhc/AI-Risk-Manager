from risk_manager.demo import run_demo_pipeline
from risk_manager.responder import (
    MockActionAdapter,
    ResponseResult,
    ResponseAction,
)


def test_demo_pipeline_executes_all_scenarios():
    results = run_demo_pipeline(verbose=False)

    assert len(results) == 5
    scenario_names = [r["scenario_name"] for r in results]
    assert "legitimate_control" in scenario_names
    assert "return_abuse" in scenario_names
    assert "transaction_fraud" in scenario_names
    assert "fraud_spike" in scenario_names
    assert "abuse_ring" in scenario_names

    decisions = {r["decision"] for r in results}
    assert "MANUAL_REVIEW" in decisions

    for entry in results:
        assert entry["merchant_id"] in {"merchant_a", "merchant_b", "merchant_c"}
        assert entry["amount"] > 0
        assert 0.0 <= entry["detector_confidence"] <= 1.0
        assert 0.0 <= entry["verifier_risk_score"] <= 1.0
        assert entry["verifier_status"] in {"VERIFIED_SUSPICIOUS", "VERIFIED_NOT_SUSPICIOUS", "INCONCLUSIVE"}
        assert len(entry["shap_top_features"]) >= 1
        assert "feature" in entry["shap_top_features"][0]
        assert "contribution" in entry["shap_top_features"][0]
        assert entry["decision"] in {"ALLOW", "MONITOR", "MANUAL_REVIEW", "BLOCK", "APPROVE", "DEFENSIVE_ACTION"}
        assert entry["selected_expected_loss"] >= 0.0
        assert entry["response_action_code"] != ""
        assert entry["mock_execution_status"] == "SUCCESS"
        assert len(entry["mock_executed_steps"]) >= 1
        assert entry["audit_id"].startswith("aud_")


def test_mock_action_adapter_defensive_actions():
    adapter = MockActionAdapter(mode="simulation")

    action_codes = [
        ("STANDARD_APPROVAL", "ALLOW", "gateway_capture_id"),
        ("FLAG_RETURN_FOR_STAFF_REVIEW", "QUEUE_MANUAL_REVIEW", "case_ticket_id"),
        ("STEP_UP_AUTHENTICATION_AND_REVIEW", "QUEUE_MANUAL_REVIEW", "challenge_id"),
        ("ALERT_OPS_TEAM_FOR_REVIEW", "ALERT_AND_QUEUE", "secops_alert_id"),
        ("INVESTIGATION_CASE_QUEUE", "QUEUE_MANUAL_REVIEW", "investigation_case_id"),
        ("SUSPEND_RETURN_PRIVILEGES", "DEFENSIVE_CONTROL", "policy_enforcement_id"),
        ("DECLINE_AND_NOTIFY", "DEFENSIVE_CONTROL", "gateway_decline_ref"),
        ("THROTTLE_VELOCITY_AND_ALERT_SECURITY", "DEFENSIVE_CONTROL", "incident_id"),
        ("QUARANTINE_LINKED_ENTITIES", "DEFENSIVE_CONTROL", "quarantine_batch_id"),
    ]

    for code, act_type, expected_ref_key in action_codes:
        mock_response = ResponseResult(
            response_id="resp_test_01",
            event_id="evt_test_01",
            merchant_id="merchant_a",
            decision="DEFENSIVE_ACTION" if act_type == "DEFENSIVE_CONTROL" else "MANUAL_REVIEW",
            case_type="transaction_fraud",
            action=ResponseAction(
                action_code=code,
                action_type=act_type,
                message=f"Test message for {code}",
                instructions={"review_queue": "test_queue"},
            ),
            risk_score=0.75,
            confidence=0.85,
            rationale=["Test rationale"],
        )

        receipt = adapter.execute(mock_response)
        assert receipt.status == "SUCCESS"
        assert receipt.simulated is True
        assert receipt.action_code == code
        assert len(receipt.executed_steps) >= 1
        assert expected_ref_key in receipt.external_reference_ids
