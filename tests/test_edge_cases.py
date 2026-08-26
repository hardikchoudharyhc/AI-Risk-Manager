from datetime import datetime, timezone
from decimal import Decimal
import pytest
from pydantic import ValidationError

from risk_manager.config import MAPPINGS
from risk_manager.models import Transaction, Customer, Order
from risk_manager.normalize import normalize_record
from risk_manager.pipeline import process_records
from risk_manager.features import FeatureEngine


def test_malformed_input_date_parsing_fallback():
    """Test malformed timestamp formats are quarantined during pipeline processing."""
    record = {
        "cust_id": "C-EDGE-01",
        "order_id": "O-EDGE-01",
        "order_total": "50.00",
        "pay_type": "card",
        "order_dt": "invalid-timestamp-string",
        "currency": "USD",
        "transaction_status": "completed",
    }
    valid, stats = process_records([record], MAPPINGS["merchant_a"], Transaction)
    assert len(valid) == 0
    assert stats.invalid_records == 1


def test_invalid_negative_and_zero_amount():
    """Test validation rejects negative or zero amount records."""
    record_neg = {
        "cust_id": "C-EDGE-02",
        "order_id": "O-EDGE-02",
        "order_total": "-100.00",
        "pay_type": "card",
        "order_dt": "2026-08-23T10:00:00Z",
        "currency": "USD",
        "transaction_status": "completed",
    }
    record_zero = {
        "cust_id": "C-EDGE-03",
        "order_id": "O-EDGE-03",
        "order_total": "0.00",
        "pay_type": "card",
        "order_dt": "2026-08-23T10:00:00Z",
        "currency": "USD",
        "transaction_status": "completed",
    }
    valid, stats = process_records([record_neg, record_zero], MAPPINGS["merchant_a"], Transaction)
    assert len(valid) == 0
    assert stats.invalid_records == 2


def test_missing_required_fields_quarantining():
    """Test records missing required fields (e.g. empty order_id or missing customer_id) are quarantined."""
    record_missing_cust = {
        "order_id": "O-EDGE-04",
        "order_total": "50.00",
        "pay_type": "card",
        "order_dt": "2026-08-23T10:00:00Z",
        "currency": "USD",
        "transaction_status": "completed",
    }
    record_empty_id = {
        "cust_id": "C-EDGE-05",
        "order_id": "",
        "order_total": "50.00",
        "pay_type": "card",
        "order_dt": "2026-08-23T10:00:00Z",
        "currency": "USD",
        "transaction_status": "completed",
    }
    valid, stats = process_records([record_missing_cust, record_empty_id], MAPPINGS["merchant_a"], Transaction)
    assert len(valid) == 0
    assert stats.invalid_records == 2


def test_duplicate_records_detection():
    """Test pipeline detects and quarantines duplicate record identifiers."""
    rec = {
        "cust_id": "C-DUP-1",
        "order_id": "O-DUP-1",
        "order_total": "25.00",
        "pay_type": "card",
        "order_dt": "2026-08-23T10:00:00Z",
        "currency": "USD",
        "transaction_status": "completed",
    }
    valid, stats = process_records([rec, rec], MAPPINGS["merchant_a"], Transaction)
    assert len(valid) == 1
    assert stats.duplicate_records == 1
    assert stats.valid_records == 1


def test_unknown_payment_category_normalization():
    """Test normalization handles unknown or exotic payment method strings gracefully."""
    record = {
        "cust_id": "C-UNK-1",
        "order_id": "O-UNK-1",
        "order_total": "75.00",
        "pay_type": "crypto_barter_token",
        "order_dt": "2026-08-23T10:00:00Z",
        "currency": "USD",
        "transaction_status": "completed",
    }
    normalized = normalize_record(record, MAPPINGS["merchant_a"])
    txn = Transaction.model_validate(normalized)
    assert txn.payment_method == "CRYPTO_BARTER_TOKEN"


def test_unseen_merchant_schema_mapping_behavior():
    """Test passing an unseen merchant mapping configuration."""
    unseen_mapping = {
        "client_code": "customer_id",
        "ref_number": "transaction_id",
        "order_number": "order_id",
        "billing_total": "amount",
        "payment_channel": "payment_method",
        "tx_date": "timestamp",
        "currency": "currency",
        "transaction_status": "transaction_status",
    }
    raw_unseen = {
        "client_code": "CLIENT-99",
        "ref_number": "TXN-999",
        "order_number": "ORD-999",
        "billing_total": "120.50",
        "payment_channel": "apple pay",
        "tx_date": "2026-08-23T14:30:00Z",
        "currency": "USD",
        "transaction_status": "COMPLETED",
    }
    valid, stats = process_records([raw_unseen], unseen_mapping, Transaction)
    assert stats.valid_records == 1
    assert valid[0].customer_id == "CLIENT-99"
    assert valid[0].amount == Decimal("120.50")
    assert valid[0].payment_method == "APPLE PAY"


def test_new_customer_zero_history_feature_extraction():
    """Test FeatureEngine extracts features for a completely new customer with no prior history safely."""
    new_txn = Transaction(
        transaction_id="TXN-NEW-01",
        order_id="ORD-NEW-01",
        customer_id="C-NEW-CUSTOMER",
        amount=Decimal("150.00"),
        currency="USD",
        payment_method="CARD",
        transaction_status="PENDING",
        timestamp=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
    )
    engine = FeatureEngine(
        transactions=[new_txn],
        orders=[],
        returns=[],
        chargebacks=[],
        customers=[],
        devices=[],
        addresses=[],
        prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
    )

    ra_features = engine.extract_return_abuse_features(new_txn)
    assert ra_features.customer_order_count == 0
    assert ra_features.customer_return_count == 0
    assert ra_features.customer_return_rate == 0.0

    tf_features = engine.extract_transaction_fraud_features(new_txn)
    assert tf_features.transaction_velocity_24h == 0.0
    assert tf_features.customer_failed_transaction_count == 0

    ar_features = engine.extract_abuse_ring_features(new_txn)
    assert ar_features.devices_per_customer == 0
    assert ar_features.accounts_per_device == 0
