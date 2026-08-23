"""Synthetic labeled dataset for detector training/validation/testing."""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import random

from risk_manager.models import (
    Customer, Order, Transaction, Return, Chargeback, Device, Address
)


def safe_divide(num: Decimal, denom: Decimal) -> Decimal:
    """Safe division."""
    return num / denom if denom > 0 else Decimal("1")


def generate_labeled_dataset(
    num_samples: int = 400,
    seed: int = 42,
    class_distribution: dict[str, float] = None,
) -> list[tuple]:
    """Generate synthetic labeled (features_dict, case_type) pairs.
    
    case_type: "return_abuse", "transaction_fraud", "fraud_spike", "abuse_ring", "normal"
    """
    random.seed(seed)
    
    if class_distribution is None:
        class_distribution = {
            "return_abuse": 0.25,
            "transaction_fraud": 0.25,
            "fraud_spike": 0.20,
            "abuse_ring": 0.20,
            "normal": 0.10,
        }
    
    base_time = datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc)
    dataset = []
    
    for sample_idx in range(num_samples):
        # Assign class
        class_type = random.choices(
            list(class_distribution.keys()),
            weights=list(class_distribution.values()),
            k=1
        )[0]
        
        customer_id = f"CUST-{sample_idx:04d}"
        transaction_id = f"TXN-{sample_idx:04d}"
        order_id = f"ORD-{sample_idx:04d}"
        
        # Generate features based on class
        features = _generate_features_for_class(
            class_type, customer_id, transaction_id, order_id, base_time
        )
        
        dataset.append((features, class_type))
    
    return dataset


def _generate_features_for_class(
    class_type: str, cust_id: str, txn_id: str, ord_id: str, base_time: datetime
) -> dict:
    """Generate feature dict with class-specific characteristics + noise + overlap.
    
    Creates more realistic, ambiguous cases:
    - Shared ranges across classes
    - Noisy features
    - Edge cases and boundary violations
    """
    
    # Base shared ranges (all classes can have overlapping ranges)
    shared_order_count = random.randint(2, 80)
    shared_return_count = random.randint(0, 20)
    shared_amount = Decimal(str(random.uniform(20, 500)))
    shared_velocity = random.uniform(0.0, 3.0)
    shared_acct_age = random.randint(1, 1000)
    
    # Class-specific modifiers (add noise, reduce determinism)
    if class_type == "return_abuse":
        # Elevated return rate, but with noise and cases where it's low
        return_rate = random.uniform(0.3, 0.95) if random.random() > 0.2 else random.uniform(0.0, 0.3)
        order_value_modifier = random.uniform(1.5, 3.0) if random.random() > 0.3 else random.uniform(0.8, 2.0)
        velocity_modifier = random.uniform(0.0, 0.5) if random.random() > 0.2 else random.uniform(0.5, 2.0)
        failed_rate = random.uniform(0.0, 0.2)
        
    elif class_type == "transaction_fraud":
        # High velocity, high failed rate, but some legitimate-looking frauds
        return_rate = random.uniform(0.0, 0.4)
        order_value_modifier = random.uniform(1.5, 5.0) if random.random() > 0.4 else random.uniform(0.8, 1.5)
        velocity_modifier = random.uniform(0.1, 2.0) if random.random() > 0.1 else random.uniform(0.0, 0.3)
        failed_rate = random.uniform(0.1, 0.9) if random.random() > 0.3 else random.uniform(0.0, 0.2)
        
    elif class_type == "fraud_spike":
        # High volume but normal structure (legitimate-looking spike)
        return_rate = random.uniform(0.0, 0.2)
        order_value_modifier = random.uniform(0.8, 1.5) if random.random() > 0.2 else random.uniform(1.5, 3.0)
        velocity_modifier = random.uniform(1.5, 8.0) if random.random() > 0.1 else random.uniform(0.0, 1.0)
        failed_rate = random.uniform(0.0, 0.3)
        
    elif class_type == "abuse_ring":
        # High device/account linkage, but some legitimate multi-device users
        return_rate = random.uniform(0.0, 0.4)
        order_value_modifier = random.uniform(0.8, 2.5)
        velocity_modifier = random.uniform(0.2, 2.0) if random.random() > 0.3 else random.uniform(0.0, 0.5)
        failed_rate = random.uniform(0.0, 0.3)
        
    else:  # "normal"
        # Clean behavior, but with occasional anomalies
        return_rate = random.uniform(0.0, 0.15) if random.random() > 0.1 else random.uniform(0.15, 0.5)
        order_value_modifier = random.uniform(0.7, 1.5) if random.random() > 0.1 else random.uniform(1.5, 3.0)
        velocity_modifier = random.uniform(0.0, 0.2) if random.random() > 0.1 else random.uniform(0.2, 1.5)
        failed_rate = random.uniform(0.0, 0.05) if random.random() > 0.1 else random.uniform(0.05, 0.3)
    
    # Add noise to all features
    noise = lambda: random.gauss(0, 0.1)
    
    order_value = Decimal(str(max(10, float(shared_amount) * order_value_modifier * (1 + noise()))))
    avg_order_value = Decimal(str(max(10, float(shared_amount) * (0.7 + random.random()) * (1 + noise()))))
    
    return {
        "customer_order_count": max(1, int(shared_order_count * (1 + noise() * 0.3))),
        "customer_return_count": max(0, int(shared_return_count * (1 + noise() * 0.5))),
        "customer_return_rate": max(0, min(1, return_rate + noise() * 0.15)),
        "customer_avg_order_value": avg_order_value,
        "order_value": order_value,
        "order_value_vs_avg_ratio": float(safe_divide(order_value, avg_order_value)),
        "amount": order_value,
        "customer_avg_transaction_amount": avg_order_value,
        "amount_vs_avg_ratio": float(safe_divide(order_value, avg_order_value)),
        "transaction_velocity_24h": max(0, shared_velocity * velocity_modifier * (1 + noise() * 0.2)),
        "transaction_velocity_1h": max(0, shared_velocity * velocity_modifier * 0.5 * (1 + noise() * 0.2)),
        "customer_failed_transaction_count": max(0, int(random.uniform(0, 10) * failed_rate * (1 + noise() * 0.3))),
        "customer_failed_transaction_rate": max(0, min(1, failed_rate + noise() * 0.1)),
        "unusual_payment_method": random.random() < (0.3 if class_type in ["transaction_fraud", "abuse_ring"] else 0.1),
        "customer_account_age_days": max(1, int(shared_acct_age * (1 + noise() * 0.2))),
        "devices_per_customer": max(1, int(random.randint(1, 8) * (0.5 if class_type == "abuse_ring" else random.uniform(0.8, 1.2)))),
        "accounts_per_device": max(1, int(random.randint(1, 6) * (random.uniform(1, 3) if class_type == "abuse_ring" else random.uniform(0.8, 1.2)))),
    }
