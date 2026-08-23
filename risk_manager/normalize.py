from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


PAYMENT_METHODS = {
    "upi": "UPI",
    "unified payments interface": "UPI",
    "card": "CARD",
    "credit card": "CARD",
    "debit card": "CARD",
    "wallet": "WALLET",
}


def normalize_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        if "/" in text:
            text = text.replace("/", "-")
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_amount(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"invalid amount: {value!r}") from error
    return amount.quantize(Decimal("0.01"))


def normalize_payment_method(value: Any) -> str:
    key = str(value).strip().lower()
    return PAYMENT_METHODS.get(key, key.upper())


def normalize_record(record: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    normalized = {canonical: record[source] for source, canonical in mapping.items() if source in record}
    if "transaction_id" not in normalized and "order_id" in normalized:
        normalized["transaction_id"] = normalized["order_id"]
    for field in ("timestamp", "account_created_at", "first_seen", "last_seen"):
        if field in normalized and normalized[field] not in (None, ""):
            normalized[field] = normalize_timestamp(normalized[field])
    if "amount" in normalized:
        normalized["amount"] = normalize_amount(normalized["amount"])
    if "payment_method" in normalized:
        normalized["payment_method"] = normalize_payment_method(normalized["payment_method"])
    for field in ("currency", "transaction_status", "return_status", "status"):
        if field in normalized and isinstance(normalized[field], str):
            normalized[field] = normalized[field].strip().upper()
    return normalized