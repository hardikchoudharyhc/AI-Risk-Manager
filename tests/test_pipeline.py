from datetime import timezone
from decimal import Decimal

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