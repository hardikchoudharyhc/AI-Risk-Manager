from pathlib import Path

from .config import MAPPINGS
from .ingestion.api_connector import SimulatedApiConnector
from .ingestion.csv_connector import CsvConnector
from .ingestion.json_connector import JsonConnector
from .models import Transaction
from .pipeline import process_records

ROOT = Path(__file__).parents[1]


def main() -> None:
    sources = [
        ("merchant_a", CsvConnector(ROOT / "data" / "synthetic" / "merchant_a.csv")),
        ("merchant_b", JsonConnector(ROOT / "data" / "synthetic" / "merchant_b.json")),
        ("merchant_c", SimulatedApiConnector(lambda: [{
            "user_id": "C-301", "order_ref": "ORD-C-1", "transaction_value": "49.5",
            "payment": "Unified Payments Interface", "date": "2026-08-23T10:00:00+05:30",
            "currency_code": "inr", "status": "completed",
        }])),
    ]
    for merchant, connector in sources:
        records, stats = process_records(connector.read(), MAPPINGS[merchant], Transaction)
        print(f"{merchant}: {stats.valid_records} valid, {stats.invalid_records} invalid")
        for record in records:
            print(record.model_dump(mode="json"))


if __name__ == "__main__":
    main()