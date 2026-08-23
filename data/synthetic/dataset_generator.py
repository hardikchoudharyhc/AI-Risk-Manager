from datetime import datetime, timedelta, timezone
from decimal import Decimal

from risk_manager.models import (
    Customer, Order, Transaction, Return, Chargeback, Device, Address
)


def create_synthetic_dataset(base_time: datetime = None) -> tuple:
    """Create synthetic canonical dataset for testing and inspection."""
    base_time = base_time or datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc)
    
    # Customers
    customers = [
        Customer(
            customer_id="C-001",
            account_age_days=365,
            location="US-NY",
            account_created_at=base_time - timedelta(days=365)
        ),
        Customer(
            customer_id="C-002",
            account_age_days=30,
            location="US-CA",
            account_created_at=base_time - timedelta(days=30)
        ),
        Customer(
            customer_id="C-003",
            account_age_days=1,
            location="US-TX",
            account_created_at=base_time - timedelta(days=1)
        ),
    ]
    
    # Orders
    orders = [
        Order(
            order_id="ORD-001",
            customer_id="C-001",
            product_id="P-A",
            amount=Decimal("50.00"),
            currency="USD",
            timestamp=base_time - timedelta(days=30),
            order_status="COMPLETED",
            delivery_status="DELIVERED"
        ),
        Order(
            order_id="ORD-002",
            customer_id="C-001",
            product_id="P-B",
            amount=Decimal("75.00"),
            currency="USD",
            timestamp=base_time - timedelta(days=15),
            order_status="COMPLETED",
            delivery_status="DELIVERED"
        ),
        Order(
            order_id="ORD-003",
            customer_id="C-001",
            product_id="P-A",
            amount=Decimal("200.00"),
            currency="USD",
            timestamp=base_time - timedelta(hours=2),
            order_status="PENDING",
            delivery_status=None
        ),
        Order(
            order_id="ORD-004",
            customer_id="C-002",
            product_id="P-C",
            amount=Decimal("30.00"),
            currency="USD",
            timestamp=base_time - timedelta(hours=1),
            order_status="COMPLETED",
            delivery_status="DELIVERED"
        ),
    ]
    
    # Transactions
    transactions = [
        Transaction(
            transaction_id="TXN-001",
            order_id="ORD-001",
            customer_id="C-001",
            amount=Decimal("50.00"),
            currency="USD",
            payment_method="UPI",
            transaction_status="COMPLETED",
            timestamp=base_time - timedelta(days=30),
        ),
        Transaction(
            transaction_id="TXN-002",
            order_id="ORD-002",
            customer_id="C-001",
            amount=Decimal("75.00"),
            currency="USD",
            payment_method="CARD",
            transaction_status="COMPLETED",
            timestamp=base_time - timedelta(days=15),
        ),
        Transaction(
            transaction_id="TXN-003",
            order_id="ORD-003",
            customer_id="C-001",
            amount=Decimal("200.00"),
            currency="USD",
            payment_method="WALLET",
            transaction_status="PENDING",
            timestamp=base_time - timedelta(hours=1),
        ),
        Transaction(
            transaction_id="TXN-004",
            order_id="ORD-004",
            customer_id="C-002",
            amount=Decimal("30.00"),
            currency="USD",
            payment_method="CARD",
            transaction_status="COMPLETED",
            timestamp=base_time - timedelta(hours=1),
        ),
    ]
    
    # Returns
    returns = [
        Return(
            return_id="RET-001",
            order_id="ORD-001",
            customer_id="C-001",
            return_reason="DEFECTIVE",
            return_status="APPROVED",
            timestamp=base_time - timedelta(days=25),
        ),
    ]
    
    # Chargebacks
    chargebacks = [
        Chargeback(
            chargeback_id="CB-001",
            transaction_id="TXN-002",
            customer_id="C-001",
            reason="UNAUTHORIZED",
            status="OPEN",
            timestamp=base_time - timedelta(days=5),
        ),
    ]
    
    # Devices
    devices = [
        Device(
            device_id="DEV-001",
            customer_id="C-001",
            first_seen=base_time - timedelta(days=30),
            last_seen=base_time - timedelta(hours=1),
        ),
        Device(
            device_id="DEV-002",
            customer_id="C-001",
            first_seen=base_time - timedelta(days=15),
            last_seen=base_time - timedelta(hours=1),
        ),
        Device(
            device_id="DEV-003",
            customer_id="C-002",
            first_seen=base_time - timedelta(hours=2),
            last_seen=base_time - timedelta(hours=1),
        ),
    ]
    
    # Addresses
    addresses = [
        Address(
            address_id="ADDR-001",
            customer_id="C-001",
            location="123 Main St, NY"
        ),
        Address(
            address_id="ADDR-002",
            customer_id="C-002",
            location="456 Oak Ave, CA"
        ),
    ]
    
    return customers, orders, transactions, returns, chargebacks, devices, addresses
