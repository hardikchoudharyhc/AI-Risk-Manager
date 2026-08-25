from datetime import datetime, timedelta, timezone
from decimal import Decimal

from risk_manager.models import (
    Customer, Order, Transaction, Return, Chargeback, Device, Address
)


def create_synthetic_dataset(base_time: datetime = None) -> tuple:
    """Create synthetic canonical dataset for testing and inspection."""
    base_time = base_time or datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc)
    
    # Existing Customers
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
        # Control Scenario Customer (Legitimate baseline)
        Customer(
            customer_id="C-NORM-100",
            account_age_days=365,
            location="US-WA",
            account_created_at=base_time - timedelta(days=365)
        ),
    # Return Abuse Customer
    Customer(
        customer_id="C-RA-100",
        account_age_days=120,
        location="US-IL",
        account_created_at=base_time - timedelta(days=120)
    ),
    # Transaction Fraud Customer
    Customer(
        customer_id="C-TF-100",
        account_age_days=14,
        location="US-FL",
        account_created_at=base_time - timedelta(days=14)
    ),
    # Fraud Spike Customer
    Customer(
        customer_id="C-FS-100",
        account_age_days=90,
        location="US-OH",
        account_created_at=base_time - timedelta(days=90)
    ),
    # Abuse Ring Customers (8 accounts)
    Customer(customer_id="C-RING-100", account_age_days=60, location="US-NV", account_created_at=base_time - timedelta(days=60)),
    Customer(customer_id="C-RING-101", account_age_days=60, location="US-NV", account_created_at=base_time - timedelta(days=60)),
    Customer(customer_id="C-RING-102", account_age_days=60, location="US-NV", account_created_at=base_time - timedelta(days=60)),
    Customer(customer_id="C-RING-103", account_age_days=60, location="US-NV", account_created_at=base_time - timedelta(days=60)),
    Customer(customer_id="C-RING-104", account_age_days=60, location="US-NV", account_created_at=base_time - timedelta(days=60)),
    Customer(customer_id="C-RING-105", account_age_days=60, location="US-NV", account_created_at=base_time - timedelta(days=60)),
    Customer(customer_id="C-RING-106", account_age_days=60, location="US-NV", account_created_at=base_time - timedelta(days=60)),
    Customer(customer_id="C-RING-107", account_age_days=60, location="US-NV", account_created_at=base_time - timedelta(days=60)),
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

    # Control Scenario Orders (Clean history)
    for idx, days_ago in enumerate([150, 120, 90, 60, 45, 30, 20, 10, 5, 2], 1):
        orders.append(
            Order(
                order_id=f"ORD-NORM-HIST-{idx}",
                customer_id="C-NORM-100",
                product_id="P-CLEAN",
                amount=Decimal("50.00"),
                currency="USD",
                timestamp=base_time - timedelta(days=days_ago),
                order_status="COMPLETED",
                delivery_status="DELIVERED"
            )
        )
    orders.append(
        Order(
            order_id="ORD-NORM-100",
            customer_id="C-NORM-100",
            product_id="P-CLEAN",
            amount=Decimal("52.00"),
            currency="USD",
            timestamp=base_time - timedelta(minutes=30),
            order_status="PENDING",
            delivery_status=None
        )
    )

    # Return Abuse Scenario Orders (6 historical + 1 current pending)
    ra_history_orders = [
        ("ORD-RA-HIST-1", Decimal("100.00"), 60),
        ("ORD-RA-HIST-2", Decimal("90.00"), 45),
        ("ORD-RA-HIST-3", Decimal("110.00"), 30),
        ("ORD-RA-HIST-4", Decimal("95.00"), 20),
        ("ORD-RA-HIST-5", Decimal("105.00"), 10),
        ("ORD-RA-HIST-6", Decimal("100.00"), 5),
    ]
    for oid, amt, days_ago in ra_history_orders:
        orders.append(
            Order(
                order_id=oid,
                customer_id="C-RA-100",
                product_id="P-FASHION",
                amount=amt,
                currency="USD",
                timestamp=base_time - timedelta(days=days_ago),
                order_status="COMPLETED",
                delivery_status="DELIVERED"
            )
        )
    orders.append(
        Order(
            order_id="ORD-RA-100",
            customer_id="C-RA-100",
            product_id="P-LUXURY",
            amount=Decimal("180.00"),
            currency="USD",
            timestamp=base_time - timedelta(minutes=45),
            order_status="PENDING",
            delivery_status=None
        )
    )

    # Transaction Fraud Scenario Orders
    for idx in range(1, 5):
        orders.append(
            Order(
                order_id=f"ORD-TF-HIST-{idx}",
                customer_id="C-TF-100",
                product_id="P-ELEC",
                amount=Decimal("30.00"),
                currency="USD",
                timestamp=base_time - timedelta(days=10),
                order_status="COMPLETED",
                delivery_status="DELIVERED"
            )
        )
    orders.append(
        Order(
            order_id="ORD-TF-100",
            customer_id="C-TF-100",
            product_id="P-HIGHVAL",
            amount=Decimal("320.00"),
            currency="USD",
            timestamp=base_time - timedelta(minutes=5),
            order_status="PENDING",
            delivery_status=None
        )
    )

    # Fraud Spike Scenario Orders
    for idx, mins_ago in enumerate([1440, 1080, 720, 360], 1):
        orders.append(
            Order(
                order_id=f"ORD-FS-HIST-{idx}",
                customer_id="C-FS-100",
                product_id="P-DIGITAL",
                amount=Decimal("40.00"),
                currency="USD",
                timestamp=base_time - timedelta(minutes=mins_ago),
                order_status="COMPLETED",
                delivery_status="DELIVERED"
            )
        )
    orders.append(
        Order(
            order_id="ORD-FS-100",
            customer_id="C-FS-100",
            product_id="P-DIGITAL",
            amount=Decimal("130.00"),
            currency="USD",
            timestamp=base_time - timedelta(minutes=5),
            order_status="PENDING",
            delivery_status=None
        )
    )

    # Abuse Ring Scenario Orders
    orders.append(
        Order(
            order_id="ORD-RING-100",
            customer_id="C-RING-100",
            product_id="P-GIFT",
            amount=Decimal("220.00"),
            currency="USD",
            timestamp=base_time - timedelta(minutes=10),
            order_status="PENDING",
            delivery_status=None
        )
    )

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

    # Control Scenario Transactions
    for idx, days_ago in enumerate([150, 120, 90, 60, 45, 30, 20, 10, 5, 2], 1):
        transactions.append(
            Transaction(
                transaction_id=f"TXN-NORM-HIST-{idx}",
                order_id=f"ORD-NORM-HIST-{idx}",
                customer_id="C-NORM-100",
                amount=Decimal("50.00"),
                currency="USD",
                payment_method="CARD",
                transaction_status="COMPLETED",
                timestamp=base_time - timedelta(days=days_ago),
            )
        )
    txn_norm_control = Transaction(
        transaction_id="TXN-NORM-100",
        order_id="ORD-NORM-100",
        customer_id="C-NORM-100",
        amount=Decimal("50.00"),
        currency="USD",
        payment_method="CARD",
        transaction_status="PENDING",
        timestamp=base_time - timedelta(minutes=30),
    )
    transactions.append(txn_norm_control)

    # Return Abuse Scenario Transactions
    for idx, (oid, amt, days_ago) in enumerate(ra_history_orders, 1):
        transactions.append(
            Transaction(
                transaction_id=f"TXN-RA-HIST-{idx}",
                order_id=oid,
                customer_id="C-RA-100",
                amount=amt,
                currency="USD",
                payment_method="CARD",
                transaction_status="COMPLETED",
                timestamp=base_time - timedelta(days=days_ago),
            )
        )
    txn_ra_demo = Transaction(
        transaction_id="TXN-RA-100",
        order_id="ORD-RA-100",
        customer_id="C-RA-100",
        amount=Decimal("180.00"),
        currency="USD",
        payment_method="WALLET",
        transaction_status="PENDING",
        timestamp=base_time - timedelta(minutes=45),
    )
    transactions.append(txn_ra_demo)

    # Transaction Fraud Scenario Transactions (baseline + burst of failed transactions)
    for idx in range(1, 5):
        transactions.append(
            Transaction(
                transaction_id=f"TXN-TF-HIST-{idx}",
                order_id=f"ORD-TF-HIST-{idx}",
                customer_id="C-TF-100",
                amount=Decimal("30.00"),
                currency="USD",
                payment_method="CARD",
                transaction_status="COMPLETED",
                timestamp=base_time - timedelta(days=10),
            )
        )
    # Burst failed txns in last hour
    for idx, (amt, mins_ago) in enumerate([("32.00", 40), ("35.00", 30), ("30.00", 20)], 1):
        transactions.append(
            Transaction(
                transaction_id=f"TXN-TF-FAIL-{idx}",
                order_id=f"ORD-TF-FAIL-{idx}",
                customer_id="C-TF-100",
                amount=Decimal(amt),
                currency="USD",
                payment_method="CARD",
                transaction_status="FAILED",
                timestamp=base_time - timedelta(minutes=mins_ago),
            )
        )
    txn_tf_demo = Transaction(
        transaction_id="TXN-TF-100",
        order_id="ORD-TF-100",
        customer_id="C-TF-100",
        amount=Decimal("320.00"),
        currency="USD",
        payment_method="CRYPTO",
        transaction_status="PENDING",
        timestamp=base_time - timedelta(minutes=5),
    )
    transactions.append(txn_tf_demo)

    # Fraud Spike Scenario Transactions (24h baseline + 1h velocity spike)
    for idx, mins_ago in enumerate([1440, 1080, 720, 360], 1):
        transactions.append(
            Transaction(
                transaction_id=f"TXN-FS-HIST-{idx}",
                order_id=f"ORD-FS-HIST-{idx}",
                customer_id="C-FS-100",
                amount=Decimal("40.00"),
                currency="USD",
                payment_method="CARD",
                transaction_status="COMPLETED",
                timestamp=base_time - timedelta(minutes=mins_ago),
            )
        )
    for idx, mins_ago in enumerate([55, 48, 40, 35, 25, 20, 15, 10], 1):
        transactions.append(
            Transaction(
                transaction_id=f"TXN-FS-REC-{idx}",
                order_id=f"ORD-FS-REC-{idx}",
                customer_id="C-FS-100",
                amount=Decimal("40.00"),
                currency="USD",
                payment_method="CARD",
                transaction_status="COMPLETED",
                timestamp=base_time - timedelta(minutes=mins_ago),
            )
        )
    txn_fs_demo = Transaction(
        transaction_id="TXN-FS-100",
        order_id="ORD-FS-100",
        customer_id="C-FS-100",
        amount=Decimal("42.00"),
        currency="USD",
        payment_method="CARD",
        transaction_status="PENDING",
        timestamp=base_time - timedelta(minutes=5),
    )
    transactions.append(txn_fs_demo)

    # Abuse Ring Scenario Transactions (other linked ring accounts transactions)
    ring_methods = ["CARD", "UPI", "WALLET", "NETBANKING"]
    for idx, c_ring_id in enumerate(["C-RING-101", "C-RING-102", "C-RING-103", "C-RING-104", "C-RING-105", "C-RING-106", "C-RING-107"], 1):
        for sub_idx in range(1, 3):
            transactions.append(
                Transaction(
                    transaction_id=f"TXN-RING-OTHER-{idx}-{sub_idx}",
                    order_id=f"ORD-RING-OTHER-{idx}-{sub_idx}",
                    customer_id=c_ring_id,
                    amount=Decimal("60.00"),
                    currency="USD",
                    payment_method=ring_methods[(idx + sub_idx) % len(ring_methods)],
                    transaction_status="COMPLETED",
                    timestamp=base_time - timedelta(days=2, hours=idx),
                )
            )
    transactions.append(
        Transaction(
            transaction_id="TXN-RING-HIST-1",
            order_id="ORD-RING-HIST-1",
            customer_id="C-RING-100",
            amount=Decimal("60.00"),
            currency="USD",
            payment_method="CARD",
            transaction_status="COMPLETED",
            timestamp=base_time - timedelta(days=5),
        )
    )
    transactions.append(
        Transaction(
            transaction_id="TXN-RING-HIST-2",
            order_id="ORD-RING-HIST-2",
            customer_id="C-RING-100",
            amount=Decimal("60.00"),
            currency="USD",
            payment_method="CARD",
            transaction_status="COMPLETED",
            timestamp=base_time - timedelta(days=2),
        )
    )
    txn_ring_demo = Transaction(
        transaction_id="TXN-RING-100",
        order_id="ORD-RING-100",
        customer_id="C-RING-100",
        amount=Decimal("90.00"),
        currency="USD",
        payment_method="GIFT_CARD",
        transaction_status="PENDING",
        timestamp=base_time - timedelta(minutes=10),
    )
    transactions.append(txn_ring_demo)

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
        # Return Abuse Scenario returns (3 returns out of 6 orders)
        Return(
            return_id="RET-RA-01",
            order_id="ORD-RA-HIST-1",
            customer_id="C-RA-100",
            return_reason="CHANGED_MIND",
            return_status="APPROVED",
            timestamp=base_time - timedelta(days=55),
        ),
        Return(
            return_id="RET-RA-02",
            order_id="ORD-RA-HIST-3",
            customer_id="C-RA-100",
            return_reason="NOT_AS_DESCRIBED",
            return_status="APPROVED",
            timestamp=base_time - timedelta(days=25),
        ),
        Return(
            return_id="RET-RA-03",
            order_id="ORD-RA-HIST-5",
            customer_id="C-RA-100",
            return_reason="DEFECTIVE",
            return_status="APPROVED",
            timestamp=base_time - timedelta(days=8),
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
        # Transaction Fraud Scenario chargeback
        Chargeback(
            chargeback_id="CB-TF-01",
            transaction_id="TXN-TF-HIST-1",
            customer_id="C-TF-100",
            reason="UNAUTHORIZED_CARD_USE",
            status="OPEN",
            timestamp=base_time - timedelta(days=2),
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
        Device(device_id="DEV-NORM-100", customer_id="C-NORM-100", first_seen=base_time - timedelta(days=365), last_seen=base_time - timedelta(minutes=30)),
        Device(device_id="DEV-RA-100", customer_id="C-RA-100", first_seen=base_time - timedelta(days=120), last_seen=base_time - timedelta(minutes=45)),
        Device(device_id="DEV-TF-100", customer_id="C-TF-100", first_seen=base_time - timedelta(days=14), last_seen=base_time - timedelta(minutes=5)),
        Device(device_id="DEV-FS-100", customer_id="C-FS-100", first_seen=base_time - timedelta(days=90), last_seen=base_time - timedelta(minutes=5)),
        Device(device_id="DEV-RING-100-SECONDARY", customer_id="C-RING-100", first_seen=base_time - timedelta(days=30), last_seen=base_time - timedelta(minutes=10)),
    ]
    # Shared device for Abuse Ring accounts
    for c_ring_id in ["C-RING-100", "C-RING-101", "C-RING-102", "C-RING-103", "C-RING-104", "C-RING-105", "C-RING-106", "C-RING-107"]:
        devices.append(
            Device(
                device_id="DEV-RING-SHARED",
                customer_id=c_ring_id,
                first_seen=base_time - timedelta(days=60),
                last_seen=base_time - timedelta(minutes=10),
            )
        )

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
        Address(address_id="ADDR-NORM-100", customer_id="C-NORM-100", location="789 Pine St, WA"),
        Address(address_id="ADDR-RA-100", customer_id="C-RA-100", location="321 Elm St, IL"),
        Address(address_id="ADDR-TF-100", customer_id="C-TF-100", location="654 Maple Dr, FL"),
        Address(address_id="ADDR-FS-100", customer_id="C-FS-100", location="987 Cedar Rd, OH"),
    ]
    # Shared address for Abuse Ring accounts
    for c_ring_id in ["C-RING-100", "C-RING-101", "C-RING-102", "C-RING-103", "C-RING-104", "C-RING-105", "C-RING-106", "C-RING-107"]:
        addresses.append(
            Address(
                address_id="ADDR-RING-SHARED",
                customer_id=c_ring_id,
                location="555 Coordinated Hub, NV",
            )
        )

    return customers, orders, transactions, returns, chargebacks, devices, addresses
