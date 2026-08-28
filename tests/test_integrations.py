import pytest
from fastapi.testclient import TestClient

from risk_manager.api.app import app
from risk_manager.integrations import (
    registry,
    GenericAPIProvider,
    ShopifyProvider,
    RazorpayProvider,
    MerchantConnection,
    validate_api_url,
)

client = TestClient(app)


def test_integration_provider_registry():
    """Test provider registration and retrieval."""
    assert registry.get_provider("shopify") is not None
    assert registry.get_provider("razorpay") is not None
    assert registry.get_provider("generic_api") is not None
    assert registry.get_provider("nonexistent") is None

    providers = registry.list_providers()
    provider_ids = [p["provider_id"] for p in providers]
    assert "shopify" in provider_ids
    assert "razorpay" in provider_ids
    assert "generic_api" in provider_ids


def test_list_integrations_endpoint():
    """Test GET /integrations returns available provider list."""
    res = client.get("/integrations")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 3


def test_connect_provider_endpoint():
    """Test POST /integrations/{provider}/connect creates connection and hides secrets."""
    payload = {
        "merchant_id": "merchant_test_01",
        "credentials": {
            "api_endpoint": "https://api.my-store.com/v1/txns",
            "api_key": "secret_key_12345"
        }
    }
    res = client.post("/integrations/generic_api/connect", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert "connection_id" in data
    assert data["merchant_id"] == "merchant_test_01"
    assert data["provider"] == "generic_api"
    assert data["status"] == "active"
    # Secrets should not be exposed in raw returned dict
    assert "encrypted_credentials" not in data
    assert "api_key" not in data.get("metadata", {})


def test_get_connection_endpoint():
    """Test GET /integrations/{connection_id} returns connection status."""
    # First create connection
    conn = MerchantConnection(
        merchant_id="merchant_test_02",
        provider="shopify",
        metadata={"shop_domain": "my-shop.myshopify.com"}
    )
    registry.add_connection(conn)

    res = client.get(f"/integrations/{conn.connection_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["connection_id"] == conn.connection_id
    assert data["merchant_id"] == "merchant_test_02"
    assert data["provider"] == "shopify"


def test_sync_connection_endpoint():
    """Test POST /integrations/{connection_id}/sync triggers pipeline execution."""
    conn = MerchantConnection(
        merchant_id="merchant_test_sync",
        provider="generic_api",
        metadata={"api_endpoint": "https://api.merchant.com/v1/txns"}
    )
    registry.add_connection(conn)

    res = client.post(f"/integrations/{conn.connection_id}/sync")
    assert res.status_code == 200
    data = res.json()

    assert data["connection_id"] == conn.connection_id
    assert data["merchant_id"] == "merchant_test_sync"
    assert data["synced_records"] > 0
    assert len(data["pipeline_results"]) > 0
    assert "risk_assessment" in data["pipeline_results"][0]


def test_webhook_endpoint_processing_and_deduplication():
    """Test POST /webhooks/{provider} receives, verifies, and processes event with deduplication."""
    payload = {
        "id": "pay_TEST_WEBHOOK_01",
        "entity": "payment",
        "amount": 15000,
        "currency": "INR",
        "status": "captured",
        "order_id": "order_TEST_WEBHOOK_01",
        "customer_id": "cust_TEST_W01",
        "method": "card",
        "created_at": 1700000000
    }
    headers = {"X-Razorpay-Event-Id": "evt_rzp_unique_101"}

    # First attempt: processed
    res1 = client.post("/webhooks/razorpay", json=payload, headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "processed"
    assert data1["processed_records"] == 1

    # Second attempt (same event_id): duplicate skipped
    res2 = client.post("/webhooks/razorpay", json=payload, headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "duplicate_skipped"
    assert data2["processed_records"] == 0


def test_invalid_provider_returns_404():
    """Test requesting invalid provider returns 404."""
    res1 = client.post("/integrations/invalid_provider/connect", json={"merchant_id": "m1"})
    assert res1.status_code == 404

    res2 = client.post("/webhooks/invalid_provider", json={})
    assert res2.status_code == 404


def test_invalid_connection_id_returns_404():
    """Test non-existent connection_id returns 404."""
    res1 = client.get("/integrations/conn_nonexistent_999")
    assert res1.status_code == 404

    res2 = client.post("/integrations/conn_nonexistent_999/sync")
    assert res2.status_code == 404


def test_generic_api_url_security_validation():
    """Test SSRF & loopback protection on API URL inputs."""
    valid, msg = validate_api_url("https://api.stripe.com/v1/charges")
    assert valid is True

    # Loopback / internal addresses must be rejected
    invalid_urls = [
        "http://localhost:8000/api",
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.1.1/config",
        "file:///etc/passwd",
    ]
    for url in invalid_urls:
        val, err = validate_api_url(url)
        assert val is False, f"URL {url} should have been rejected for security reasons."


# --- RAZORPAY API-KEY MOCK MVP TESTS ---

def test_razorpay_mock_valid_credential_flow():
    """1. Test valid Razorpay mock credential flow (rzp_test_mock / mock_secret)."""
    payload = {
        "key_id": "rzp_test_mock",
        "key_secret": "mock_secret",
        "merchant_id": "merchant_razorpay_mock"
    }
    res = client.post("/integrations/razorpay/connect", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "active"
    assert data["provider"] == "razorpay"
    assert data["metadata"]["environment"] == "MOCK / DEMO"
    assert data["metadata"]["is_mock"] is True
    assert "connection_id" in data
    assert "mock_secret" not in res.text
    assert "encrypted_credentials" not in data


def test_razorpay_invalid_credentials():
    """2. Test invalid Razorpay mock credentials return clean error."""
    payload = {
        "key_id": "rzp_test_mock",
        "key_secret": "invalid_wrong_secret",
        "merchant_id": "merchant_razorpay_02"
    }
    res = client.post("/integrations/razorpay/connect", json=payload)
    assert res.status_code == 400
    data = res.json()
    err_msg = data.get("detail") or data.get("error", {}).get("message", "")
    assert "Razorpay" in err_msg or "failed" in err_msg or "mock" in err_msg


def test_razorpay_mock_transaction_fetch_returns_20_records():
    """3. Test mock transaction fetch returns 20 deterministic records."""
    from risk_manager.integrations.razorpay.mock_provider import MockRazorpayProvider

    mock_items = MockRazorpayProvider.get_mock_payments()
    assert len(mock_items) == 20
    assert mock_items[0]["id"] == "pay_RZP_MOCK_101"
    assert mock_items[-1]["id"] == "pay_RZP_MOCK_120"


def test_razorpay_mapper_response_mapping():
    """4. Test Razorpay payment payload mapping to canonical schema."""
    from risk_manager.integrations.razorpay.mapper import map_razorpay_payment_to_canonical

    raw = {
        "id": "pay_RZP98765",
        "entity": "payment",
        "amount": 45000,  # 450.00 INR
        "currency": "inr",
        "status": "captured",
        "order_id": "order_RZP98765",
        "customer_id": "cust_RZP987",
        "method": "upi",
        "email": "user@example.com",
        "created_at": 1700000000
    }
    txn = map_razorpay_payment_to_canonical(raw)

    assert txn.transaction_id == "pay_RZP98765"
    assert txn.order_id == "order_RZP98765"
    assert txn.customer_id == "cust_RZP987"
    assert float(txn.amount) == 450.00
    assert txn.currency == "INR"
    assert txn.payment_method == "UPI"
    assert txn.transaction_status == "COMPLETED"


def test_razorpay_mapper_missing_canonical_fields():
    """5. Test missing required ID or invalid amount raises clear error."""
    from risk_manager.integrations.razorpay.mapper import map_razorpay_payment_to_canonical

    with pytest.raises(ValueError, match="payment ID"):
        map_razorpay_payment_to_canonical({"amount": 1000})

    with pytest.raises(ValueError, match="greater than zero"):
        map_razorpay_payment_to_canonical({"id": "pay_1", "amount": 0})


def test_razorpay_amount_conversion():
    """6. Test paise-to-Rupee major unit conversion."""
    from risk_manager.integrations.razorpay.mapper import map_razorpay_payment_to_canonical

    raw = {"id": "pay_AMT_1", "amount": 25000, "currency": "INR"}
    txn = map_razorpay_payment_to_canonical(raw)
    assert float(txn.amount) == 250.00


def test_razorpay_currency_mapping():
    """7. Test currency uppercase mapping."""
    from risk_manager.integrations.razorpay.mapper import map_razorpay_payment_to_canonical

    raw = {"id": "pay_CURR_1", "amount": 1000, "currency": "usd"}
    txn = map_razorpay_payment_to_canonical(raw)
    assert txn.currency == "USD"


def test_razorpay_payment_status_mapping():
    """8. Test payment status mapping."""
    from risk_manager.integrations.razorpay.mapper import map_razorpay_payment_to_canonical

    txn_cap = map_razorpay_payment_to_canonical({"id": "p1", "amount": 1000, "status": "captured"})
    assert txn_cap.transaction_status == "COMPLETED"

    txn_auth = map_razorpay_payment_to_canonical({"id": "p2", "amount": 1000, "status": "authorized"})
    assert txn_auth.transaction_status == "PENDING"

    txn_fail = map_razorpay_payment_to_canonical({"id": "p3", "amount": 1000, "status": "failed"})
    assert txn_fail.transaction_status == "FAILED"


def test_razorpay_successful_routing_into_m1_m9():
    """9 & 10. Test full end-to-end Razorpay sync and M1-M9 pipeline execution for 20 mock records."""
    conn_res = client.post(
        "/integrations/razorpay/connect",
        json={"key_id": "rzp_test_mock", "key_secret": "mock_secret"}
    )
    assert conn_res.status_code == 200
    conn_id = conn_res.json()["connection_id"]

    sync_res = client.post(f"/integrations/razorpay/sync", json={"connection_id": conn_id})
    assert sync_res.status_code == 200
    data = sync_res.json()

    assert data["provider"] == "razorpay"
    assert data["synced_records"] == 20
    assert len(data["pipeline_results"]) == 20

    first_item = data["pipeline_results"][0]
    assert "risk_assessment" in first_item
    assert "decision" in first_item
    assert "response" in first_item
    assert "audit" in first_item


def test_razorpay_secret_never_returned_or_logged():
    """11. Test key_secret is never exposed in connection list or safe_dict."""
    connect_payload = {
        "key_id": "rzp_test_mock",
        "key_secret": "mock_secret",
        "merchant_id": "merchant_sec"
    }
    res = client.post("/integrations/razorpay/connect", json=connect_payload)
    assert res.status_code == 200
    raw_str = res.text

    assert "mock_secret" not in raw_str

    conn_id = res.json()["connection_id"]
    get_res = client.get(f"/integrations/{conn_id}")
    assert get_res.status_code == 200
    assert "mock_secret" not in get_res.text


# --- RAZORPAY MOCK TWO-WAY OUTBOUND TESTS ---

def test_razorpay_outbound_single_result():
    """Test sending a single M1-M9 risk result outbound to mock Razorpay provider."""
    from risk_manager.integrations import registry
    provider_inst = registry.get_provider("razorpay")
    conn = provider_inst.authenticate("merchant_test", {"key_id": "rzp_test_mock", "key_secret": "mock_secret"})

    mock_result = {
        "transaction_id": "pay_RZP_MOCK_101",
        "risk_level": "HIGH",
        "decision": "DEFENSIVE_ACTION",
        "response_action_code": "FLAG_SUSPICIOUS"
    }
    ack = provider_inst.send_risk_result(conn, mock_result)

    assert ack["success"] is True
    assert ack["provider"] == "razorpay"
    assert ack["mode"] == "mock"
    assert ack["transaction_id"] == "pay_RZP_MOCK_101"
    assert ack["risk_status"] == "HIGH"
    assert ack["decision"] == "DEFENSIVE_ACTION"
    assert ack["action"] == "FLAG_SUSPICIOUS"


def test_razorpay_outbound_batch_results():
    """Test sending batch of 20 M1-M9 risk results outbound to mock Razorpay provider."""
    from risk_manager.integrations import registry
    provider_inst = registry.get_provider("razorpay")
    conn = provider_inst.authenticate("merchant_test", {"key_id": "rzp_test_mock", "key_secret": "mock_secret"})

    results_batch = [
        {
            "transaction_id": f"pay_RZP_MOCK_{101+i}",
            "risk_level": "LOW" if i % 2 == 0 else "HIGH",
            "decision": "APPROVE" if i % 2 == 0 else "MANUAL_REVIEW",
            "response_action_code": "APPROVE" if i % 2 == 0 else "FLAG_SUSPICIOUS"
        }
        for i in range(20)
    ]
    batch_ack = provider_inst.send_batch_risk_results(conn, results_batch)

    assert batch_ack["success"] is True
    assert batch_ack["total_sent"] == 20
    assert batch_ack["total_acknowledged"] == 20
    assert len(batch_ack["acknowledgements"]) == 20
    assert batch_ack["acknowledgements"][0]["transaction_id"] == "pay_RZP_MOCK_101"


def test_razorpay_outbound_api_endpoint():
    """Test POST /integrations/razorpay/outbound API endpoint."""
    conn_res = client.post(
        "/integrations/razorpay/connect",
        json={"key_id": "rzp_test_mock", "key_secret": "mock_secret"}
    )
    assert conn_res.status_code == 200
    conn_id = conn_res.json()["connection_id"]

    sample_results = [
        {"transaction_id": "pay_RZP_MOCK_101", "risk_level": "LOW", "decision": "APPROVE"},
        {"transaction_id": "pay_RZP_MOCK_102", "risk_level": "HIGH", "decision": "DEFENSIVE_ACTION"},
    ]
    outbound_res = client.post(
        "/integrations/razorpay/outbound",
        json={"connection_id": conn_id, "results": sample_results}
    )
    assert outbound_res.status_code == 200
    data = outbound_res.json()
    assert data["success"] is True
    assert data["total_sent"] == 2
    assert data["total_acknowledged"] == 2
    assert "mock_secret" not in outbound_res.text


def test_razorpay_outbound_failed_invalid_connection():
    """Test outbound dispatch fails cleanly with invalid connection."""
    from risk_manager.integrations import registry
    from risk_manager.integrations.base import MerchantConnection
    provider_inst = registry.get_provider("razorpay")

    invalid_conn = MerchantConnection(
        merchant_id="bad_merchant",
        provider="razorpay",
        status="inactive",
        metadata={"key_id": "invalid_key"}
    )
    with pytest.raises(ValueError, match="Outbound risk result"):
        provider_inst.send_risk_result(invalid_conn, {"transaction_id": "tx_1"})

