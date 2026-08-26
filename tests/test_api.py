import pytest
from fastapi.testclient import TestClient
from risk_manager.api.app import app

client = TestClient(app)


def test_health_endpoint():
    """Test GET /health returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-risk-manager"
    assert "timestamp" in data


def test_risk_analyze_valid_request():
    """Test POST /risk/analyze with valid transaction request."""
    payload = {
        "merchant_id": "merchant_b",
        "transaction_id": "TXN-API-TEST-01",
        "order_id": "ORD-API-TEST-01",
        "customer_id": "C-TF-100",
        "amount": 320.00,
        "currency": "USD",
        "payment_method": "CARD",
        "transaction_status": "PENDING",
    }
    response = client.post("/risk/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["transaction_id"] == "TXN-API-TEST-01"
    assert data["merchant_id"] == "merchant_b"
    assert "case_type" in data
    assert 0.0 <= data["detector_confidence"] <= 1.0
    assert data["verifier_status"] in {"VERIFIED_SUSPICIOUS", "VERIFIED_NOT_SUSPICIOUS", "INCONCLUSIVE"}
    assert 0.0 <= data["verifier_risk_score"] <= 1.0
    assert isinstance(data["evidence_reasons"], list)
    assert isinstance(data["shap_explanation"], list)
    assert data["decision"] in {"APPROVE", "MANUAL_REVIEW", "DEFENSIVE_ACTION"}
    assert isinstance(data["expected_losses"], dict)
    assert "APPROVE" in data["expected_losses"]
    assert "MANUAL_REVIEW" in data["expected_losses"]
    assert "DEFENSIVE_ACTION" in data["expected_losses"]
    assert data["responder_action_code"] != ""
    assert data["responder_action_type"] != ""
    assert data["defensive_message"] != ""
    assert data["mock_execution_status"] == "SUCCESS"
    assert data["audit_id"].startswith("aud_")
    assert "detector_model_version" in data["model_versions"]


def test_risk_analyze_invalid_request():
    """Test POST /risk/analyze with invalid amount <= 0 returns 422 error."""
    payload = {
        "merchant_id": "merchant_a",
        "transaction_id": "TXN-INVALID-01",
        "order_id": "ORD-INVALID-01",
        "customer_id": "C-001",
        "amount": -50.00,  # Invalid amount
        "currency": "USD",
        "payment_method": "CARD",
        "transaction_status": "PENDING",
    }
    response = client.post("/risk/analyze", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_risk_analyze_missing_required_field():
    """Test POST /risk/analyze with missing required transaction_id returns 422 error."""
    payload = {
        "merchant_id": "merchant_a",
        "order_id": "ORD-INVALID-02",
        "customer_id": "C-001",
        "amount": 100.00,
    }
    response = client.post("/risk/analyze", json=payload)
    assert response.status_code == 422


def test_risk_analyze_end_to_end_scenarios():
    """Test POST /risk/analyze for legitimate control scenario."""
    payload = {
        "merchant_id": "merchant_a",
        "transaction_id": "TXN-NORM-100",
        "order_id": "ORD-NORM-100",
        "customer_id": "C-NORM-100",
        "amount": 35.00,
        "currency": "USD",
        "payment_method": "CARD",
        "transaction_status": "PENDING",
    }
    response = client.post("/risk/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "TXN-NORM-100"
    assert data["case_type"] == "normal"
    assert data["verifier_status"] == "VERIFIED_NOT_SUSPICIOUS"
