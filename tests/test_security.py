import pytest

from risk_manager.config import MAPPINGS
from risk_manager.ingestion.csv_connector import CsvConnector
from risk_manager.models import Transaction
from risk_manager.normalize import normalize_record
from risk_manager.pipeline import process_records
from risk_manager.security import (
    validate_file_upload,
    parse_and_validate_input,
    sanitize_display_text,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_RECORD_COUNT,
)


def test_oversized_upload_rejection():
    large_bytes = b"a" * (MAX_UPLOAD_SIZE_BYTES + 100)
    is_valid, msg = validate_file_upload(large_bytes, "test.csv")
    assert is_valid is False
    assert "exceeds maximum allowed limit" in msg


def test_empty_upload_rejection():
    is_valid, msg = validate_file_upload(b"   \n\t  ", "test.csv")
    assert is_valid is False
    assert "empty" in msg


def test_invalid_file_extension_rejection():
    is_valid, msg = validate_file_upload(b"some content", "test.exe")
    assert is_valid is False
    assert "Invalid file format" in msg


def test_invalid_encoding_rejection():
    invalid_utf8 = b"\x80\x81\x82\xff"
    is_valid, msg = validate_file_upload(invalid_utf8, "test.csv")
    assert is_valid is False
    assert "encoding" in msg


def test_malformed_csv_handling():
    records, err = parse_and_validate_input("cust_id,order_id\n1,2,3,4,5\n\"unclosed quote", "csv")
    assert isinstance(records, list)
    # Each row should be a dict with non-None keys
    for r in records:
        assert None not in r


def test_malformed_json_handling():
    records, err = parse_and_validate_input("{invalid_json: true,", "json")
    assert records == []
    assert "Malformed JSON" in err


def test_excessive_record_count_rejection():
    large_json = [{"cust_id": f"C-{i}", "order_id": f"O-{i}"} for i in range(MAX_RECORD_COUNT + 10)]
    import json
    content = json.dumps(large_json)
    records, err = parse_and_validate_input(content, "json")
    assert records == []
    assert "exceeds maximum allowed batch limit" in err


def test_invalid_negative_amount_canonical_rejection():
    raw = {
        "cust_id": "A-1",
        "order_id": "O-1",
        "order_total": "-50.00",
        "pay_type": "upi",
        "order_dt": "2026-08-23T08:00:00Z",
        "currency": "USD",
        "transaction_status": "COMPLETED",
    }
    valid, stats = process_records([raw], MAPPINGS["merchant_a"], Transaction)
    assert len(valid) == 0
    assert stats.invalid_records == 1


def test_invalid_timestamp_canonical_rejection():
    raw = {
        "cust_id": "A-1",
        "order_id": "O-1",
        "order_total": "50.00",
        "pay_type": "upi",
        "order_dt": "not-a-valid-date",
        "currency": "USD",
        "transaction_status": "COMPLETED",
    }
    valid, stats = process_records([raw], MAPPINGS["merchant_a"], Transaction)
    assert len(valid) == 0
    assert stats.invalid_records == 1


def test_unexpected_and_malformed_fields_handling():
    raw = {
        "cust_id": "A-1",
        "order_id": "O-1",
        "order_total": "50.00",
        "pay_type": "upi",
        "order_dt": "2026-08-23T08:00:00Z",
        "currency": "USD",
        "transaction_status": "COMPLETED",
        "malformed_field": {"nested": [1, 2, 3]},
        "unknown_extra_field": "some_value",
    }
    valid, stats = process_records([raw], MAPPINGS["merchant_a"], Transaction)
    assert stats.valid_records == 1
    assert valid[0].customer_id == "A-1"


def test_suspicious_script_string_handling():
    script_payload = "<script>alert('xss')</script>"
    raw = {
        "cust_id": script_payload,
        "order_id": "O-SCRIPT-1",
        "order_total": "100.00",
        "pay_type": "card",
        "order_dt": "2026-08-23T08:00:00Z",
        "currency": "USD",
        "transaction_status": "COMPLETED",
    }
    valid, stats = process_records([raw], MAPPINGS["merchant_a"], Transaction)
    assert stats.valid_records == 1
    assert valid[0].customer_id == script_payload  # Plain data preserved
    sanitized = sanitize_display_text(valid[0].customer_id)
    assert "&lt;script&gt;" in sanitized
    assert "<script>" not in sanitized


def test_valid_merchant_a_twenty_records_still_works(tmp_path):
    csv_path = tmp_path / "merchant_a_20.csv"
    header = "cust_id, order_id, order_total, pay_type, order_dt, currency, transaction_status\n"
    rows = [
        f"A-1{i:02d}, O-1{i:02d}, {10 + i}.50, upi, 2026-08-23T08:00:00Z, usd, completed\n"
        for i in range(20)
    ]
    csv_path.write_text(header + "".join(rows))
    connector = CsvConnector(csv_path)
    records = connector.read()
    valid, stats = process_records(records, MAPPINGS["merchant_a"], Transaction)
    assert stats.total_records == 20
    assert stats.valid_records == 20
    assert stats.invalid_records == 0
