from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from risk_manager.models import Transaction


def map_razorpay_payment_to_canonical(data: dict[str, Any]) -> Transaction:
    """
    Convert raw Razorpay payment object into canonical Transaction model.

    Razorpay Payment Schema:
    - id: str (e.g. 'pay_K123456789')
    - order_id: str | None (e.g. 'order_K123456789')
    - customer_id: str | None (e.g. 'cust_K123456789')
    - amount: int/float (amount in paise/sub-units, e.g. 25000 = 250.00 INR)
    - currency: str (e.g. 'INR')
    - method: str (e.g. 'upi', 'card', 'netbanking', 'wallet')
    - status: str (e.g. 'captured', 'authorized', 'failed', 'refunded')
    - created_at: int/float or str (epoch seconds or ISO timestamp)
    - email: str | None
    - contact: str | None
    """
    if not isinstance(data, dict):
        raise ValueError("Razorpay payment record must be a dictionary.")

    # 1. Transaction ID
    txn_id = str(data.get("id") or data.get("transaction_id") or "").strip()
    if not txn_id:
        raise ValueError("Missing required Razorpay payment ID.")

    # 2. Order ID
    order_id = str(data.get("order_id") or "").strip()
    if not order_id:
        order_id = txn_id

    # 3. Customer ID derivation
    customer_id = str(data.get("customer_id") or "").strip()
    if not customer_id:
        email = str(data.get("email") or "").strip()
        contact = str(data.get("contact") or "").strip()
        if email and "@" in email:
            safe_email_user = email.split("@")[0].replace(".", "_")
            customer_id = f"C-RZP-{safe_email_user}"
        elif contact:
            safe_contact = contact.replace("+", "").replace(" ", "").replace("-", "")
            customer_id = f"C-RZP-{safe_contact}"
        else:
            customer_id = f"C-RZP-{txn_id.replace('pay_', '')}"

    # 4. Amount conversion (sub-units/paise -> major currency units)
    raw_amount = data.get("amount")
    if raw_amount is None:
        raise ValueError("Missing required payment amount.")

    try:
        amount_num = Decimal(str(raw_amount))
        # If amount is an integer >= 100 or clearly in paise/sub-units, divide by 100
        # Exception: if caller already converted to float major units (e.g. 250.00)
        if isinstance(raw_amount, int) or (isinstance(raw_amount, str) and raw_amount.isdigit()):
            amount_decimal = amount_num / Decimal("100")
        else:
            amount_decimal = amount_num
    except Exception as exc:
        raise ValueError(f"Invalid monetary amount format '{raw_amount}': {str(exc)}") from exc

    if amount_decimal <= 0:
        raise ValueError(f"Transaction amount must be strictly greater than zero. Received: {amount_decimal}")

    # 5. Currency
    currency = str(data.get("currency") or "INR").strip().upper()
    if len(currency) != 3:
        raise ValueError(f"Currency code must be 3 letters (e.g. INR, USD). Received: '{currency}'")

    # 6. Payment Method Mapping
    raw_method = str(data.get("method") or data.get("payment_method") or "CARD").strip().lower()
    method_map = {
        "card": "CARD",
        "credit card": "CARD",
        "debit card": "CARD",
        "upi": "UPI",
        "netbanking": "NETBANKING",
        "wallet": "WALLET",
        "emi": "CARD",
    }
    payment_method = method_map.get(raw_method, raw_method.upper())

    # 7. Status Mapping
    raw_status = str(data.get("status") or data.get("transaction_status") or "captured").strip().lower()
    status_map = {
        "captured": "COMPLETED",
        "authorized": "PENDING",
        "failed": "FAILED",
        "refunded": "REFUNDED",
        "settled": "COMPLETED",
    }
    txn_status = status_map.get(raw_status, raw_status.upper())

    # 8. Timestamp
    raw_time = data.get("created_at") or data.get("timestamp")
    if raw_time is None:
        txn_timestamp = datetime.now(timezone.utc)
    elif isinstance(raw_time, (int, float)):
        txn_timestamp = datetime.fromtimestamp(float(raw_time), tz=timezone.utc)
    elif isinstance(raw_time, str):
        raw_str = raw_time.strip()
        if raw_str.isdigit():
            txn_timestamp = datetime.fromtimestamp(float(raw_str), tz=timezone.utc)
        else:
            try:
                txn_timestamp = datetime.fromisoformat(raw_str.replace("Z", "+00:00"))
            except Exception:
                txn_timestamp = datetime.now(timezone.utc)
    else:
        txn_timestamp = datetime.now(timezone.utc)

    try:
        return Transaction(
            transaction_id=txn_id,
            order_id=order_id,
            customer_id=customer_id,
            amount=amount_decimal,
            currency=currency,
            payment_method=payment_method,
            transaction_status=txn_status,
            timestamp=txn_timestamp,
        )
    except ValidationError as exc:
        raise ValueError(f"Canonical Transaction validation failed: {str(exc)}") from exc
