import io
import csv
import json
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

CANONICAL_FIELDS = {
    "transaction_id",
    "order_id",
    "customer_id",
    "amount",
    "currency",
    "payment_method",
    "transaction_status",
    "timestamp",
}


def compact_key(k: Any) -> str:
    """Normalize key string by removing whitespace, quotes, BOM, underscores, dashes, and lowercasing."""
    if k is None:
        return ""
    s = str(k).strip('\ufeff"\' \t\r\n').lower()
    for ch in ("_", "-", " "):
        s = s.replace(ch, "")
    return s


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
    """
    Robustly normalize raw dict (from CSV or JSON) into canonical Transaction fields.
    Uses mapped schema definitions and compact key fallback matching.
    """
    clean_raw = {}
    clean_compact = {}
    for k, v in record.items():
        if k is not None:
            raw_k = str(k).strip('\ufeff"\' \t\r\n')
            val_clean = v.strip(' \t\r\n') if isinstance(v, str) else v
            clean_raw[raw_k] = val_clean
            clean_compact[compact_key(raw_k)] = val_clean

    normalized = {}

    # Stage 1: Explicit mapping from detected merchant schema
    for source_key, canonical_field in mapping.items():
        src_comp = compact_key(source_key)
        if src_comp in clean_compact:
            normalized[canonical_field] = clean_compact[src_comp]
        elif source_key in clean_raw:
            normalized[canonical_field] = clean_raw[source_key]

    # Stage 2: Universal Fallback matching for canonical fields
    FIELD_ALIASES = {
        "customer_id": ["customerid", "custid", "userid", "customer_id", "cust_id", "user_id"],
        "order_id": ["orderid", "orderref", "txnid", "transactionid", "order_id", "order_ref"],
        "transaction_id": ["transactionid", "txnid", "orderid", "orderref", "transaction_id"],
        "amount": ["amount", "ordertotal", "transactionvalue", "total", "value", "price"],
        "payment_method": ["paymentmethod", "paytype", "payment", "method", "payment_method"],
        "timestamp": ["timestamp", "orderdt", "date", "time", "datetime", "createdat"],
        "currency": ["currency", "currencycode", "curr"],
        "transaction_status": ["transactionstatus", "orderstatus", "status"],
    }

    for c_field, aliases in FIELD_ALIASES.items():
        if c_field not in normalized or normalized[c_field] in (None, ""):
            for alias in aliases:
                alias_comp = compact_key(alias)
                if alias_comp in clean_compact and clean_compact[alias_comp] not in (None, ""):
                    normalized[c_field] = clean_compact[alias_comp]
                    break

    # Stage 3: Sync transaction_id and order_id
    if "transaction_id" not in normalized and "order_id" in normalized:
        normalized["transaction_id"] = normalized["order_id"]
    if "order_id" not in normalized and "transaction_id" in normalized:
        normalized["order_id"] = normalized["transaction_id"]

    # Stage 4: Value Normalizations
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

    final_normalized = {k: v for k, v in normalized.items() if k in CANONICAL_FIELDS}
    return final_normalized


def detect_merchant_schema(records: list[dict[str, Any]]) -> tuple[str, dict[str, str]]:
    """Automatically detect merchant schema mapping based on compact key overlap."""
    from .config import MAPPINGS

    if not records:
        return "merchant_a", MAPPINGS["merchant_a"]

    sample_keys = set()
    for rec in records[:10]:
        if isinstance(rec, dict):
            for k in rec.keys():
                if k is not None:
                    sample_keys.add(compact_key(k))

    best_merchant = "merchant_a"
    best_score = -1

    for merchant_id, mapping in MAPPINGS.items():
        score = sum(1 for src in mapping.keys() if compact_key(src) in sample_keys)
        if score > best_score:
            best_score = score
            best_merchant = merchant_id

    # Check canonical fields matching
    canonical_keys = {"customerid", "orderid", "transactionid", "amount", "paymentmethod", "timestamp", "currency", "transactionstatus"}
    canonical_match_count = sum(1 for ck in canonical_keys if ck in sample_keys)

    if canonical_match_count > best_score and canonical_match_count >= 4:
        canonical_mapping = {
            "customer_id": "customer_id", "order_id": "order_id", "transaction_id": "transaction_id",
            "amount": "amount", "payment_method": "payment_method", "timestamp": "timestamp",
            "currency": "currency", "transaction_status": "transaction_status",
        }
        return "canonical", canonical_mapping

    if best_score <= 0:
        return "merchant_a", MAPPINGS["merchant_a"]

    return best_merchant, MAPPINGS[best_merchant]