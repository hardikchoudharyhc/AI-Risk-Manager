from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from risk_manager.features.base import Features, safe_divide


@dataclass
class ReturnAbuseFeatures(Features):
    """Features for Return Abuse detection.
    
    Target: is this customer/order fraudulently returning items?
    Leakage prevention: uses only pre-return data (order history, customer history).
    """
    customer_order_count: int = 0
    customer_return_count: int = 0
    customer_return_rate: float = 0.0
    customer_avg_order_value: Decimal = Decimal("0")
    order_value: Decimal = Decimal("0")
    order_value_vs_avg_ratio: float = 0.0
    category_return_rate: float = 0.0
    recent_return_frequency: float = 0.0
    days_since_last_order: int = 0
    customer_account_age_days: int = 0
    

@dataclass
class TransactionFraudFeatures(Features):
    """Features for Transaction Fraud detection.
    
    Target: is this transaction fraudulent?
    Leakage prevention: uses only pre-transaction data.
    """
    amount: Decimal = Decimal("0")
    payment_method: str = ""
    customer_avg_transaction_amount: Decimal = Decimal("0")
    amount_vs_avg_ratio: float = 0.0
    transaction_velocity_24h: float = 0.0
    transaction_velocity_1h: float = 0.0
    customer_failed_transaction_count: int = 0
    customer_failed_transaction_rate: float = 0.0
    unusual_payment_method: bool = False
    days_since_last_transaction: int = 0
    customer_account_age_days: int = 0


@dataclass
class FraudSpikeFeatures(Features):
    """Features for Fraud Spike detection.
    
    Target: is current fraud/transaction rate anomalous?
    Leakage prevention: compares recent (e.g., last 1h) vs historical baseline.
    Must NOT use future data.
    """
    current_transaction_rate_1h: float = 0.0
    historical_transaction_rate_24h_avg: float = 0.0
    transaction_rate_deviation: float = 0.0
    current_fraud_rate_1h: float = 0.0
    historical_fraud_rate_24h_avg: float = 0.0
    fraud_rate_deviation: float = 0.0
    unusual_location: bool = False
    unusual_payment_method: bool = False
    amount_stddev_deviation: float = 0.0
    spike_severity: float = 0.0


@dataclass
class AbuseRingFeatures(Features):
    """Features for Abuse Ring detection.
    
    Target: is customer part of coordinated abuse ring?
    Leakage prevention: uses aggregated graph metrics (accounts per device, etc.).
    """
    accounts_per_device: int = 0
    accounts_per_address: int = 0
    devices_per_customer: int = 0
    shared_payment_methods: int = 0
    graph_degree: int = 0
    suspicious_cluster_size: int = 0
    cluster_density: float = 0.0
    shared_device_transactions: int = 0
    unusual_account_creation_pattern: bool = False
