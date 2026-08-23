from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from risk_manager.features import FeatureEngine
from data.synthetic.dataset_generator import create_synthetic_dataset


class TestReturnAbuseFeatures:
    """Test return abuse feature extraction."""
    
    def test_return_rate_computation(self):
        """Verify return rate is computed from pre-transaction history."""
        cust, orders, txns, rets, chargebacks, devs, addrs = create_synthetic_dataset()
        engine = FeatureEngine(
            transactions=txns,
            orders=orders,
            returns=rets,
            chargebacks=chargebacks,
            customers=cust,
            devices=devs,
            addresses=addrs,
            prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        features = engine.extract_return_abuse_features(txns[2])  # TXN-003
        
        # C-001 has 3 orders pre-TXN-003: ORD-001 (day-30), ORD-002 (day-15), ORD-003 (hour-2)
        assert features.customer_order_count == 3
        assert features.customer_return_count == 1
        assert abs(features.customer_return_rate - (1/3)) < 0.01
        assert features.order_value == Decimal("200.00")
    
    def test_new_customer_no_leakage(self):
        """New customer should have zero/default features, no future data."""
        cust, orders, txns, rets, chargebacks, devs, addrs = create_synthetic_dataset()
        
        # C-003 is 1 day old, has no orders/transactions
        engine = FeatureEngine(
            transactions=txns,
            orders=orders,
            returns=rets,
            chargebacks=chargebacks,
            customers=cust,
            devices=devs,
            addresses=addrs,
            prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        # Create a new transaction for C-003
        new_txn = txns[0].__class__(
            transaction_id="TXN-NEW",
            order_id="ORD-NEW",
            customer_id="C-003",
            amount=Decimal("99.99"),
            currency="USD",
            payment_method="CARD",
            transaction_status="COMPLETED",
            timestamp=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        features = engine.extract_return_abuse_features(new_txn)
        assert features.customer_order_count == 0
        assert features.customer_return_count == 0
        assert features.customer_return_rate == 0.0


class TestTransactionFraudFeatures:
    """Test transaction fraud feature extraction."""
    
    def test_transaction_velocity(self):
        """Verify velocity is computed from pre-transaction history."""
        cust, orders, txns, rets, chargebacks, devs, addrs = create_synthetic_dataset()
        engine = FeatureEngine(
            transactions=txns,
            orders=orders,
            returns=rets,
            chargebacks=chargebacks,
            customers=cust,
            devices=devs,
            addresses=addrs,
            prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        features = engine.extract_transaction_fraud_features(txns[2])
        
        assert features.customer_avg_transaction_amount == Decimal("62.50")
        assert features.transaction_velocity_24h > 0
        assert 364 <= features.customer_account_age_days <= 365
    
    def test_failed_transaction_rate(self):
        """Verify failed transaction rate excludes current."""
        cust, orders, txns, rets, chargebacks, devs, addrs = create_synthetic_dataset()
        engine = FeatureEngine(
            transactions=txns,
            orders=orders,
            returns=rets,
            chargebacks=chargebacks,
            customers=cust,
            devices=devs,
            addresses=addrs,
            prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        features = engine.extract_transaction_fraud_features(txns[2])
        
        # TXN-001, TXN-002 are pre-TXN-003 and completed
        assert features.customer_failed_transaction_rate == 0.0
        assert features.customer_failed_transaction_count == 0


class TestFraudSpikeFeatures:
    """Test fraud spike feature extraction."""
    
    def test_spike_deviation_no_baseline(self):
        """New customer with no historical baseline."""
        cust, orders, txns, rets, chargebacks, devs, addrs = create_synthetic_dataset()
        engine = FeatureEngine(
            transactions=txns,
            orders=orders,
            returns=rets,
            chargebacks=chargebacks,
            customers=cust,
            devices=devs,
            addresses=addrs,
            prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        new_txn = txns[0].__class__(
            transaction_id="TXN-SPIKE-TEST",
            order_id="ORD-SPIKE-TEST",
            customer_id="C-003",
            amount=Decimal("1000.00"),
            currency="USD",
            payment_method="CARD",
            transaction_status="COMPLETED",
            timestamp=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        features = engine.extract_fraud_spike_features(new_txn)
        assert features.current_transaction_rate_1h == 0.0
        assert features.historical_transaction_rate_24h_avg == 0.0


class TestAbuseRingFeatures:
    """Test abuse ring feature extraction."""
    
    def test_devices_per_customer(self):
        """Verify device linkage graph features."""
        cust, orders, txns, rets, chargebacks, devs, addrs = create_synthetic_dataset()
        engine = FeatureEngine(
            transactions=txns,
            orders=orders,
            returns=rets,
            chargebacks=chargebacks,
            customers=cust,
            devices=devs,
            addresses=addrs,
            prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        features = engine.extract_abuse_ring_features(txns[0])
        
        # C-001 has 2 devices (DEV-001, DEV-002)
        assert features.devices_per_customer == 2
        assert features.graph_degree >= 2


class TestTemporalLeakagePrevention:
    """Verify no future data leaks into features."""
    
    def test_future_transactions_excluded(self):
        """Future transactions should not appear in historical features."""
        cust, orders, txns, rets, chargebacks, devs, addrs = create_synthetic_dataset()
        
        # Create a future transaction that should not leak
        future_txn = txns[0].__class__(
            transaction_id="TXN-FUTURE",
            order_id="ORD-FUTURE",
            customer_id="C-001",
            amount=Decimal("9999.00"),
            currency="USD",
            payment_method="CARD",
            transaction_status="COMPLETED",
            timestamp=datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        all_txns = txns + [future_txn]
        
        engine = FeatureEngine(
            transactions=all_txns,
            orders=orders,
            returns=rets,
            chargebacks=chargebacks,
            customers=cust,
            devices=devs,
            addresses=addrs,
            prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        features = engine.extract_transaction_fraud_features(txns[2])
        
        # Should only see TXN-001, TXN-002, not TXN-FUTURE
        assert features.customer_avg_transaction_amount == Decimal("62.50")


class TestMissingEntities:
    """Test graceful handling of missing entities."""
    
    def test_no_customer_record(self):
        """Transaction without customer record should not crash."""
        cust, orders, txns, rets, chargebacks, devs, addrs = create_synthetic_dataset()
        
        engine = FeatureEngine(
            transactions=txns,
            orders=orders,
            returns=rets,
            chargebacks=chargebacks,
            customers=[],  # No customer records
            devices=devs,
            addresses=addrs,
            prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        features = engine.extract_return_abuse_features(txns[0])
        assert features.customer_account_age_days == 0
    
    def test_no_device_records(self):
        """Abuse ring features should handle missing devices."""
        cust, orders, txns, rets, chargebacks, devs, addrs = create_synthetic_dataset()
        
        engine = FeatureEngine(
            transactions=txns,
            orders=orders,
            returns=rets,
            chargebacks=chargebacks,
            customers=cust,
            devices=[],  # No device records
            addresses=addrs,
            prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        features = engine.extract_abuse_ring_features(txns[0])
        assert features.devices_per_customer == 0
        assert features.graph_degree >= 0


class TestFeatureDataTypes:
    """Verify feature data types and serialization."""
    
    def test_to_dict_serialization(self):
        """Features should serialize to dict with standard types."""
        cust, orders, txns, rets, chargebacks, devs, addrs = create_synthetic_dataset()
        engine = FeatureEngine(
            transactions=txns,
            orders=orders,
            returns=rets,
            chargebacks=chargebacks,
            customers=cust,
            devices=devs,
            addresses=addrs,
        )
        
        features = engine.extract_return_abuse_features(txns[0])
        d = features.to_dict()
        
        assert isinstance(d, dict)
        assert isinstance(d["timestamp"], str)
        assert isinstance(d["customer_order_count"], int)
        assert isinstance(d["customer_return_rate"], (int, float))
        assert "transaction_id" in d
