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


def test_process_valid_json_array_request():
    """Test POST /process with valid JSON array of records."""
    payload = {
        "data": [
            {
                "customerId": "B-201",
                "orderId": "ORD-B-201",
                "amount": "240.00",
                "paymentMethod": "credit card",
                "timestamp": "2026/08/26 09:00:00",
                "currency": "EUR",
                "transactionStatus": "settled"
            }
        ],
        "merchant_id": "merchant_b"
    }
    response = client.post("/process", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert "request_id" in res
    assert res["summary"]["total_records"] == 1
    assert res["summary"]["valid_records"] == 1
    assert res["summary"]["merchant_id"] == "merchant_b"
    assert len(res["results"]) == 1

    item = res["results"][0]
    assert item["case_id"] == "case_ORD-B-201"
    assert item["transaction"]["transaction_id"] == "ORD-B-201"
    assert item["transaction"]["customer_id"] == "B-201"
    assert item["transaction"]["amount"] == 240.00
    assert item["transaction"]["currency"] == "EUR"

    # Risk Assessment Contract
    ra = item["risk_assessment"]
    assert "detected_case" in ra
    assert 0.0 <= ra["detector_confidence"] <= 1.0
    assert ra["verifier_status"] in {"VERIFIED_SUSPICIOUS", "VERIFIED_NOT_SUSPICIOUS", "INCONCLUSIVE"}
    assert 0.0 <= ra["verifier_risk_score"] <= 1.0
    assert isinstance(ra["evidence_reasons"], list)
    assert isinstance(ra["shap_top_features"], list)

    # Decision Contract
    dec = item["decision"]
    assert dec["final_decision"] in {"APPROVE", "MANUAL_REVIEW", "DEFENSIVE_ACTION"}
    assert "policy" in dec
    assert "APPROVE" in dec["expected_losses_by_action"]
    assert isinstance(dec["rationale"], list)

    # Response Contract
    resp = item["response"]
    assert resp["action_code"] != ""
    assert resp["action_type"] != ""
    assert resp["defensive_message"] != ""
    assert resp["execution_status"] == "SUCCESS"

    # Audit Contract
    audit = item["audit"]
    assert audit["audit_id"].startswith("aud_")
    assert audit["model_version"] != ""
    assert audit["policy_version"] != ""
    assert "timestamp" in audit


def test_process_valid_csv_string_request():
    """Test POST /process with raw CSV string payload."""
    csv_text = (
        "cust_id,order_id,order_total,pay_type,order_dt,currency,transaction_status\n"
        "A-101,ORD-A-101,125.50,upi,2026-08-26T10:00:00Z,USD,completed\n"
    )
    payload = {"data": csv_text}
    response = client.post("/process", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["summary"]["valid_records"] == 1
    assert res["results"][0]["transaction"]["transaction_id"] == "ORD-A-101"
    assert res["results"][0]["transaction"]["amount"] == 125.50


def test_process_invalid_negative_amount_error():
    """Test POST /process with negative amount returns 422 error contract."""
    payload = {
        "data": [
            {
                "cust_id": "A-101",
                "order_id": "ORD-A-101",
                "order_total": "-50.00",
                "pay_type": "upi",
                "order_dt": "2026-08-26T10:00:00Z",
                "currency": "USD",
                "transaction_status": "completed"
            }
        ]
    }
    response = client.post("/process", json=payload)
    assert response.status_code == 422
    res = response.json()
    assert "error" in res
    assert res["error"]["code"] in {"UNPROCESSABLE_ENTITY", "VALIDATION_ERROR"}
    assert "error" in res["error"]["message"].lower() or "invalid" in res["error"]["message"].lower() or "record" in res["error"]["message"].lower()


def test_process_missing_required_fields_error():
    """Test POST /process with missing transaction_id / amount returns 422 error contract."""
    payload = {
        "data": [
            {
                "pay_type": "upi"
            }
        ]
    }
    response = client.post("/process", json=payload)
    assert response.status_code == 422
    res = response.json()
    assert "error" in res
    assert res["error"]["code"] == "UNPROCESSABLE_ENTITY"


def test_process_malformed_input_error():
    """Test POST /process with malformed text data returns 400 or 422 error contract."""
    payload = {
        "data": "{malformed_json: true, missing_quotes: }"
    }
    response = client.post("/process", json=payload)
    assert response.status_code in {400, 422}
    res = response.json()
    assert "error" in res
    assert res["error"]["code"] in {"BAD_REQUEST", "UNPROCESSABLE_ENTITY", "VALIDATION_ERROR"}


def test_process_empty_data_error():
    """Test POST /process with empty data returns 400 error."""
    payload = {"data": ""}
    response = client.post("/process", json=payload)
    assert response.status_code == 400
    res = response.json()
    assert "error" in res
    assert res["error"]["code"] == "BAD_REQUEST"


# --- LEGACY CONTRACT TESTS ---

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
        "amount": -50.00,
        "currency": "USD",
        "payment_method": "CARD",
        "transaction_status": "PENDING",
    }
    response = client.post("/risk/analyze", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data or "detail" in data


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
