from datetime import timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).parents[1]

from risk_manager.config import MAPPINGS
from risk_manager.ingestion.api_connector import SimulatedApiConnector
from risk_manager.ingestion.csv_connector import CsvConnector
from risk_manager.ingestion.json_connector import JsonConnector
from risk_manager.models import Transaction
from risk_manager.pipeline import process_records


def test_three_merchant_schemas_become_canonical(tmp_path):
    csv_path = tmp_path / "merchant_a.csv"
    csv_path.write_text("cust_id,order_id,order_total,pay_type,order_dt,currency,transaction_status\n"
                        "A-1,O-1,10.5,upi,2026-08-23T08:00:00Z,usd,completed\n")
    json_path = tmp_path / "merchant_b.json"
    json_path.write_text('[{"customerId":"B-1","orderId":"O-2","amount":"20",'
                         '"paymentMethod":"credit card","timestamp":"2026/08/23 09:00:00",'
                         '"currency":"EUR","transactionStatus":"settled"}]')
    connectors = [
        ("merchant_a", CsvConnector(csv_path)),
        ("merchant_b", JsonConnector(json_path)),
        ("merchant_c", SimulatedApiConnector(lambda: [{
            "user_id": "C-1", "order_ref": "O-3", "transaction_value": 30,
            "payment": "Unified Payments Interface", "date": "2026-08-23T10:00:00+05:30",
            "currency_code": "inr", "status": "completed",
        }])),
    ]
    results = [process_records(connector.read(), MAPPINGS[name], Transaction) for name, connector in connectors]
    assert [result[1].valid_records for result in results] == [1, 1, 1]
    assert results[0][0][0].amount == Decimal("10.50")
    assert results[0][0][0].timestamp.tzinfo == timezone.utc
    assert results[1][0][0].payment_method == "CARD"
    assert results[2][0][0].payment_method == "UPI"


def test_invalid_and_duplicate_records_are_quarantined():
    records = [
        {"cust_id": "A-1", "order_id": "O-1", "order_total": "10", "pay_type": "upi",
         "order_dt": "2026-08-23T08:00:00Z", "currency": "USD", "transaction_status": "completed"},
        {"cust_id": "A-1", "order_id": "O-1", "order_total": "10", "pay_type": "upi",
         "order_dt": "2026-08-23T08:00:00Z", "currency": "USD", "transaction_status": "completed"},
        {"cust_id": "A-2", "order_id": "O-2", "order_total": "-2", "pay_type": "upi",
         "order_dt": "not-a-date", "currency": "USD", "transaction_status": "completed"},
    ]
    valid, stats = process_records(records, MAPPINGS["merchant_a"], Transaction)
    assert len(valid) == 1
    assert stats.duplicate_records == 1
    assert stats.invalid_records == 2
    assert len(stats.errors) == 2


def test_merchant_a_twenty_record_csv_ingestion(tmp_path):
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
    assert stats.duplicate_records == 0
    assert len(valid) == 20


def test_auto_schema_detection_twenty_records(tmp_path):
    from risk_manager.normalize import detect_merchant_schema
    csv_path = tmp_path / "merchant_a_20_auto.csv"
    header = "cust_id, order_id, order_total, pay_type, order_dt, currency, transaction_status\n"
    rows = [
        f"A-1{i:02d}, O-1{i:02d}, {10 + i}.50, upi, 2026-08-23T08:00:00Z, usd, completed\n"
        for i in range(20)
    ]
    csv_path.write_text(header + "".join(rows))
    connector = CsvConnector(csv_path)
    records = connector.read()
    merchant_id, mapping = detect_merchant_schema(records)
    assert merchant_id == "merchant_a"
    valid, stats = process_records(records, mapping, Transaction)
    assert stats.total_records == 20
    assert stats.valid_records == 20
    assert stats.invalid_records == 0
    assert stats.duplicate_records == 0


def test_unified_ingest_merchant_a_csv_20_records():
    from risk_manager.pipeline import ingest_raw_data
    path = ROOT / "data" / "synthetic" / "merchant_a_20.csv"
    raw_content = path.read_bytes()
    valid_txns, stats, merchant_id, fmt = ingest_raw_data(raw_content)
    assert fmt == "csv"
    assert merchant_id == "merchant_a"
    assert stats.total_records == 20
    assert stats.valid_records == 20
    assert stats.invalid_records == 0
    assert stats.duplicate_records == 0
    assert len(valid_txns) == 20


def test_unified_ingest_merchant_b_json_20_records():
    from risk_manager.pipeline import ingest_raw_data
    path = ROOT / "data" / "synthetic" / "merchant_b_20.json"
    raw_content = path.read_text()
    valid_txns, stats, merchant_id, fmt = ingest_raw_data(raw_content)
    assert fmt == "json"
    assert merchant_id == "merchant_b"
    assert stats.total_records == 20
    assert stats.valid_records == 20
    assert stats.invalid_records == 0
    assert stats.duplicate_records == 0
    assert len(valid_txns) == 20


def test_unified_ingest_canonical_json():
    from risk_manager.pipeline import ingest_raw_data
    raw_json = '[{"customer_id": "C-99", "transaction_id": "T-99", "order_id": "O-99", "amount": "99.00", "payment_method": "CARD", "timestamp": "2026-08-23T10:00:00Z", "currency": "USD", "transaction_status": "COMPLETED"}]'
    valid_txns, stats, merchant_id, fmt = ingest_raw_data(raw_json)
    assert fmt == "json"
    assert merchant_id == "canonical"
    assert stats.valid_records == 1
    assert valid_txns[0].customer_id == "C-99"


def test_unified_ingest_malformed_inputs():
    from risk_manager.pipeline import ingest_raw_data
    # Malformed JSON
    valid_txns, stats, merchant_id, fmt = ingest_raw_data("[invalid json")
    assert stats.valid_records == 0
    assert "Malformed JSON" in stats.errors[0]

    # Empty content
    valid_txns, stats, merchant_id, fmt = ingest_raw_data("   ")
    assert stats.valid_records == 0
    assert "empty" in stats.errors[0]


def test_ingest_records_with_metadata_and_source_tracking():
    from risk_manager.pipeline import ingest_records

    # CSV Test
    csv_raw = "cust_id,order_id,order_total,pay_type,order_dt,currency,transaction_status\nA-1,O-1,100.0,upi,2026-08-23T08:00:00Z,usd,completed\n"
    txns_csv, res_csv = ingest_records(csv_raw, source_type="csv", source_id="test_file.csv", merchant_id="merchant_a")
    assert len(txns_csv) == 1
    assert res_csv.source_type == "csv"
    assert res_csv.source_id == "test_file.csv"
    assert res_csv.merchant_id == "merchant_a"
    assert res_csv.valid_records == 1

    # Razorpay Adapter payload test
    rzp_raw = [{"id": "pay_mock_999", "amount": 5000, "currency": "INR", "status": "captured", "method": "card", "created_at": 1755950400}]
    from risk_manager.integrations.razorpay.mapper import map_razorpay_payment_to_canonical
    mapped_rzp = map_razorpay_payment_to_canonical(rzp_raw[0]).model_dump()
    mapped_rzp["amount"] = str(mapped_rzp["amount"])
    mapped_rzp["timestamp"] = mapped_rzp["timestamp"].isoformat()

    txns_rzp, res_rzp = ingest_records([mapped_rzp], source_type="razorpay", source_id="conn_rzp_123")
    assert len(txns_rzp) == 1
    assert res_rzp.source_type == "razorpay"
    assert res_rzp.source_id == "conn_rzp_123"
    assert txns_rzp[0].amount == Decimal("50.00")