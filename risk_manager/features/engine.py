from datetime import datetime, timedelta, timezone
from decimal import Decimal
from collections import defaultdict

from risk_manager.models import (
    Transaction, Order, Return, Chargeback, Customer, Device, Address
)
from risk_manager.features.risk_classes import (
    ReturnAbuseFeatures, TransactionFraudFeatures, 
    FraudSpikeFeatures, AbuseRingFeatures
)
from risk_manager.features.base import safe_divide, days_between, velocity


DEFAULT_BASELINE_AVG_AMOUNT = Decimal("500")


class FeatureEngine:
    """Compute features from canonical data. Prevents temporal leakage."""
    
    def __init__(
        self,
        transactions: list[Transaction],
        orders: list[Order],
        returns: list[Return],
        chargebacks: list[Chargeback],
        customers: list[Customer],
        devices: list[Device],
        addresses: list[Address],
        prediction_time: datetime = None,
    ):
        self.transactions = {t.transaction_id: t for t in transactions}
        self.orders = {o.order_id: o for o in orders}
        self.returns = {r.return_id: r for r in returns}
        self.chargebacks = {c.chargeback_id: c for c in chargebacks}
        self.customers = {c.customer_id: c for c in customers}
        self.devices = {d.device_id: d for d in devices}
        self.addresses = {a.address_id: a for a in addresses}
        
        self.prediction_time = prediction_time or datetime.now(timezone.utc)
        
        # Precompute aggregates to prevent leakage
        self._customer_orders = self._build_customer_orders()
        self._customer_transactions = self._build_customer_transactions()
        self._customer_returns = self._build_customer_returns()
        self._customer_chargebacks = self._build_customer_chargebacks()
        self._device_customers = self._build_device_customers()
        self._address_customers = self._build_address_customers()

    def register_transaction(self, transaction: Transaction) -> None:
        """Register a new transaction in feature engine and update customer aggregates."""
        self.transactions[transaction.transaction_id] = transaction
        if transaction.customer_id not in self._customer_transactions:
            self._customer_transactions[transaction.customer_id] = []
        if transaction not in self._customer_transactions[transaction.customer_id]:
            self._customer_transactions[transaction.customer_id].append(transaction)
    
    def _build_customer_orders(self) -> dict[str, list[Order]]:
        """Group orders by customer, exclude future orders."""
        agg = defaultdict(list)
        for o in self.orders.values():
            if o.timestamp <= self.prediction_time:
                agg[o.customer_id].append(o)
        return dict(agg)
    
    def _build_customer_transactions(self) -> dict[str, list[Transaction]]:
        """Group transactions by customer, exclude future."""
        agg = defaultdict(list)
        for t in self.transactions.values():
            if t.timestamp <= self.prediction_time:
                agg[t.customer_id].append(t)
        return dict(agg)
    
    def _build_customer_returns(self) -> dict[str, list[Return]]:
        """Group returns by customer, exclude future."""
        agg = defaultdict(list)
        for r in self.returns.values():
            if r.timestamp <= self.prediction_time:
                agg[r.customer_id].append(r)
        return dict(agg)
    
    def _build_customer_chargebacks(self) -> dict[str, list[Chargeback]]:
        """Group chargebacks by customer, exclude future."""
        agg = defaultdict(list)
        for c in self.chargebacks.values():
            if c.timestamp <= self.prediction_time:
                agg[c.customer_id].append(c)
        return dict(agg)
    
    def _build_device_customers(self) -> dict[str, set[str]]:
        """Map devices to customer sets."""
        agg = defaultdict(set)
        for d in self.devices.values():
            if d.first_seen <= self.prediction_time:
                agg[d.device_id].add(d.customer_id)
        return {k: len(v) for k, v in agg.items()}
    
    def _build_address_customers(self) -> dict[str, set[str]]:
        """Map addresses to customer sets."""
        agg = defaultdict(set)
        for a in self.addresses.values():
            agg[a.address_id].add(a.customer_id)
        return {k: len(v) for k, v in agg.items()}
    
    def extract_return_abuse_features(
        self, transaction: Transaction
    ) -> ReturnAbuseFeatures:
        """Extract return abuse features for a transaction/order."""
        order = self.orders.get(transaction.order_id)
        customer = self.customers.get(transaction.customer_id)
        
        # Customer history (pre-transaction)
        cust_orders = self._customer_orders.get(transaction.customer_id, [])
        cust_orders_pre = [o for o in cust_orders if o.timestamp < transaction.timestamp]
        cust_returns = self._customer_returns.get(transaction.customer_id, [])
        cust_returns_pre = [r for r in cust_returns if r.timestamp < transaction.timestamp]
        
        order_count = len(cust_orders_pre)
        return_count = len(cust_returns_pre)
        return_rate = safe_divide(return_count, order_count)
        
        if cust_orders_pre:
            avg_value = sum(o.amount for o in cust_orders_pre) / len(cust_orders_pre)
        else:
            avg_value = DEFAULT_BASELINE_AVG_AMOUNT
        
        order_value = order.amount if order else transaction.amount
        value_ratio = float(safe_divide(float(order_value), float(avg_value))) if avg_value else 0.0
        
        if cust_orders_pre:
            days_since_last = days_between(cust_orders_pre[-1].timestamp, transaction.timestamp)
        else:
            days_since_last = 0
        
        acct_age = 0
        if customer and customer.account_created_at:
            acct_age = days_between(customer.account_created_at, transaction.timestamp)
        
        return ReturnAbuseFeatures(
            transaction_id=transaction.transaction_id,
            customer_id=transaction.customer_id,
            order_id=transaction.order_id,
            timestamp=transaction.timestamp,
            customer_order_count=order_count,
            customer_return_count=return_count,
            customer_return_rate=return_rate,
            customer_avg_order_value=avg_value,
            order_value=order_value,
            order_value_vs_avg_ratio=value_ratio,
            category_return_rate=0.0,
            recent_return_frequency=0.0,
            days_since_last_order=days_since_last,
            customer_account_age_days=acct_age,
        )
    
    def extract_transaction_fraud_features(
        self, transaction: Transaction
    ) -> TransactionFraudFeatures:
        """Extract transaction fraud features."""
        customer = self.customers.get(transaction.customer_id)
        
        cust_txns = self._customer_transactions.get(transaction.customer_id, [])
        cust_txns_pre = [t for t in cust_txns if t.timestamp < transaction.timestamp]
        
        if cust_txns_pre:
            avg_amount = sum(t.amount for t in cust_txns_pre) / len(cust_txns_pre)
        else:
            avg_amount = DEFAULT_BASELINE_AVG_AMOUNT
        
        amount_ratio = float(safe_divide(float(transaction.amount), float(avg_amount))) if avg_amount else 0.0
        
        # Transaction velocity: transactions in last 24h
        txn_velocity_24 = velocity([t.timestamp for t in cust_txns_pre], 24)
        txn_velocity_1 = velocity([t.timestamp for t in cust_txns_pre], 1)
        
        # Failed transactions (assuming transaction_status != "COMPLETED" is failed)
        failed = sum(1 for t in cust_txns_pre if t.transaction_status not in ("COMPLETED", "SETTLED"))
        failed_rate = safe_divide(failed, len(cust_txns_pre)) if cust_txns_pre else (1.0 if transaction.transaction_status in ("failed", "FAILED") else 0.0)
        
        # Unusual payment method (rare method)
        method_freq = sum(1 for t in cust_txns_pre if t.payment_method == transaction.payment_method)
        unusual_method = method_freq < 1 if len(cust_txns_pre) > 0 else False
        
        days_since_last = 0
        if cust_txns_pre:
            days_since_last = days_between(cust_txns_pre[-1].timestamp, transaction.timestamp)
        
        acct_age = 0
        if customer and customer.account_created_at:
            acct_age = days_between(customer.account_created_at, transaction.timestamp)
        
        return TransactionFraudFeatures(
            transaction_id=transaction.transaction_id,
            customer_id=transaction.customer_id,
            order_id=transaction.order_id,
            timestamp=transaction.timestamp,
            amount=transaction.amount,
            payment_method=transaction.payment_method,
            customer_avg_transaction_amount=avg_amount,
            amount_vs_avg_ratio=amount_ratio,
            transaction_velocity_24h=txn_velocity_24,
            transaction_velocity_1h=txn_velocity_1,
            customer_failed_transaction_count=failed,
            customer_failed_transaction_rate=failed_rate,
            unusual_payment_method=unusual_method,
            days_since_last_transaction=days_since_last,
            customer_account_age_days=acct_age,
        )
    
    def extract_fraud_spike_features(
        self, transaction: Transaction
    ) -> FraudSpikeFeatures:
        """Extract fraud spike features. Compares recent vs historical."""
        # Recent (1h) vs historical (24h) rates
        all_cust_txns = self._customer_transactions.get(transaction.customer_id, [])
        all_pre = [t for t in all_cust_txns if t.timestamp < transaction.timestamp]
        
        now = transaction.timestamp
        recent_1h = [t for t in all_pre if t.timestamp >= now - timedelta(hours=1)]
        hist_24h = [t for t in all_pre if now - timedelta(hours=24) <= t.timestamp < now]
        
        txn_rate_1h = len(recent_1h) / 1.0  # events per hour
        txn_rate_24h = len(hist_24h) / 24.0  # events per hour
        txn_deviation = safe_divide(txn_rate_1h - txn_rate_24h, txn_rate_24h) if txn_rate_24h else 0.0
        
        # Fraud rate: chargebacks/failed transactions
        chargebacks_1h = [c for c in self._customer_chargebacks.get(transaction.customer_id, [])
                         if c.timestamp >= now - timedelta(hours=1)]
        fraud_rate_1h = len(chargebacks_1h) / 1.0
        
        chargebacks_24h = [c for c in self._customer_chargebacks.get(transaction.customer_id, [])
                          if now - timedelta(hours=24) <= c.timestamp < now]
        fraud_rate_24h = len(chargebacks_24h) / 24.0
        fraud_deviation = safe_divide(fraud_rate_1h - fraud_rate_24h, fraud_rate_24h) if fraud_rate_24h else 0.0
        
        # Amount stddev deviation
        if len(hist_24h) > 1:
            avg_amt = sum(t.amount for t in hist_24h) / len(hist_24h)
            variance = sum((float(t.amount) - float(avg_amt)) ** 2 for t in hist_24h) / len(hist_24h)
            stddev = variance ** 0.5
            current_stddev_z = (float(transaction.amount) - float(avg_amt)) / stddev if stddev > 0 else (float(transaction.amount - avg_amt) / max(1.0, float(avg_amt)))
        else:
            current_stddev_z = float(transaction.amount) / 500.0
        
        return FraudSpikeFeatures(
            transaction_id=transaction.transaction_id,
            customer_id=transaction.customer_id,
            order_id=transaction.order_id,
            timestamp=transaction.timestamp,
            current_transaction_rate_1h=txn_rate_1h,
            historical_transaction_rate_24h_avg=txn_rate_24h,
            transaction_rate_deviation=txn_deviation,
            current_fraud_rate_1h=fraud_rate_1h,
            historical_fraud_rate_24h_avg=fraud_rate_24h,
            fraud_rate_deviation=fraud_deviation,
            unusual_location=False,
            unusual_payment_method=False,
            amount_stddev_deviation=current_stddev_z,
            spike_severity=max(abs(txn_deviation), abs(fraud_deviation)),
        )
    
    def extract_abuse_ring_features(
        self, transaction: Transaction
    ) -> AbuseRingFeatures:
        """Extract abuse ring features. Requires device/address mapping."""
        # Find devices linked to this customer
        customer_devices = [d.device_id for d in self.devices.values() 
                           if d.customer_id == transaction.customer_id]
        
        # Find addresses linked to this customer
        customer_addresses = [a.address_id for a in self.addresses.values()
                             if a.customer_id == transaction.customer_id]
        
        # Count accounts per device
        avg_accounts_per_device = 0
        if customer_devices:
            total = sum(self._device_customers.get(d, 1) for d in customer_devices)
            avg_accounts_per_device = total // max(1, len(customer_devices))
        
        # Count accounts per address
        avg_accounts_per_address = 0
        if customer_addresses:
            total = sum(self._address_customers.get(a, 1) for a in customer_addresses)
            avg_accounts_per_address = total // max(1, len(customer_addresses))
        
        # Shared payment methods (same device, different customer)
        shared_methods = 0
        if customer_devices:
            linked_customers = set()
            for d in customer_devices:
                for other in self.devices.values():
                    if other.device_id == d and other.customer_id != transaction.customer_id:
                        linked_customers.add(other.customer_id)
            
            for cust_id in linked_customers:
                methods = {t.payment_method for t in self.transactions.values()
                          if t.customer_id == cust_id}
                shared_methods += len(methods)
        
        graph_degree = len(customer_devices) + len(customer_addresses)
        suspicious_cluster = max(avg_accounts_per_device, avg_accounts_per_address)
        cluster_density = safe_divide(shared_methods, max(1, graph_degree))
        
        shared_device_txns = sum(
            1 for t in self.transactions.values()
            if any(d.device_id in [device.device_id for device in self.devices.values()
                                   if device.customer_id == t.customer_id]
                   for d in self.devices.values()
                   if d.customer_id == transaction.customer_id)
            and t.customer_id != transaction.customer_id
        )
        
        return AbuseRingFeatures(
            transaction_id=transaction.transaction_id,
            customer_id=transaction.customer_id,
            order_id=transaction.order_id,
            timestamp=transaction.timestamp,
            accounts_per_device=avg_accounts_per_device,
            accounts_per_address=avg_accounts_per_address,
            devices_per_customer=len(customer_devices),
            shared_payment_methods=shared_methods,
            graph_degree=graph_degree,
            suspicious_cluster_size=suspicious_cluster,
            cluster_density=cluster_density,
            shared_device_transactions=shared_device_txns,
            unusual_account_creation_pattern=False,
        )
