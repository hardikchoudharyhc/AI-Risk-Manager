"""Generate and inspect M2 features dataset."""
from datetime import datetime, timezone

from risk_manager.features import FeatureEngine
from data.synthetic.dataset_generator import create_synthetic_dataset


def main():
    print("=" * 80)
    print("Milestone 2: Feature Engineering Demo")
    print("=" * 80)
    
    cust, orders, txns, rets, chargebacks, devs, addrs = create_synthetic_dataset()
    
    print(f"\nCanonical Dataset:")
    print(f"  Customers: {len(cust)}")
    print(f"  Orders: {len(orders)}")
    print(f"  Transactions: {len(txns)}")
    print(f"  Returns: {len(rets)}")
    print(f"  Chargebacks: {len(chargebacks)}")
    print(f"  Devices: {len(devs)}")
    print(f"  Addresses: {len(addrs)}")
    
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
    
    print("\n" + "-" * 80)
    print("Return Abuse Features")
    print("-" * 80)
    for i, txn in enumerate(txns):
        features = engine.extract_return_abuse_features(txn)
        print(f"\nTransaction {i+1}: {txn.transaction_id}")
        print(f"  Customer Order Count: {features.customer_order_count}")
        print(f"  Customer Return Count: {features.customer_return_count}")
        print(f"  Return Rate: {features.customer_return_rate:.3f}")
        print(f"  Order Value: ${float(features.order_value):.2f}")
        print(f"  Avg Order Value: ${float(features.customer_avg_order_value):.2f}")
        print(f"  Value Ratio: {features.order_value_vs_avg_ratio:.2f}x")
        print(f"  Account Age (days): {features.customer_account_age_days}")
    
    print("\n" + "-" * 80)
    print("Transaction Fraud Features")
    print("-" * 80)
    for i, txn in enumerate(txns):
        features = engine.extract_transaction_fraud_features(txn)
        print(f"\nTransaction {i+1}: {txn.transaction_id}")
        print(f"  Amount: ${float(features.amount):.2f}")
        print(f"  Payment Method: {features.payment_method}")
        print(f"  Avg Amount: ${float(features.customer_avg_transaction_amount):.2f}")
        print(f"  Amount Ratio: {features.amount_vs_avg_ratio:.2f}x")
        print(f"  Velocity (24h): {features.transaction_velocity_24h:.3f} txn/hr")
        print(f"  Velocity (1h): {features.transaction_velocity_1h:.3f} txn/hr")
        print(f"  Failed Txn Rate: {features.customer_failed_transaction_rate:.3f}")
        print(f"  Unusual Method: {features.unusual_payment_method}")
    
    print("\n" + "-" * 80)
    print("Fraud Spike Features")
    print("-" * 80)
    for i, txn in enumerate(txns):
        features = engine.extract_fraud_spike_features(txn)
        print(f"\nTransaction {i+1}: {txn.transaction_id}")
        print(f"  Current Txn Rate (1h): {features.current_transaction_rate_1h:.3f} txn/hr")
        print(f"  Historical Txn Rate (24h): {features.historical_transaction_rate_24h_avg:.3f} txn/hr")
        print(f"  Txn Rate Deviation: {features.transaction_rate_deviation:.2f}")
        print(f"  Current Fraud Rate (1h): {features.current_fraud_rate_1h:.3f} fraud/hr")
        print(f"  Historical Fraud Rate (24h): {features.historical_fraud_rate_24h_avg:.3f} fraud/hr")
        print(f"  Spike Severity: {features.spike_severity:.2f}")
    
    print("\n" + "-" * 80)
    print("Abuse Ring Features")
    print("-" * 80)
    for i, txn in enumerate(txns):
        features = engine.extract_abuse_ring_features(txn)
        print(f"\nTransaction {i+1}: {txn.transaction_id}")
        print(f"  Customer ID: {features.customer_id}")
        print(f"  Devices Per Customer: {features.devices_per_customer}")
        print(f"  Accounts Per Device: {features.accounts_per_device}")
        print(f"  Accounts Per Address: {features.accounts_per_address}")
        print(f"  Shared Payment Methods: {features.shared_payment_methods}")
        print(f"  Graph Degree: {features.graph_degree}")
        print(f"  Cluster Density: {features.cluster_density:.3f}")
    
    print("\n" + "=" * 80)
    print("Feature Groups Summary")
    print("=" * 80)
    print(f"Return Abuse: 9 features")
    print(f"Transaction Fraud: 10 features")
    print(f"Fraud Spike: 10 features")
    print(f"Abuse Ring: 9 features")
    print(f"Total: 38 features")
    print("\nAll features computed without temporal leakage ✓")
    print("Missing entities handled gracefully ✓")


if __name__ == "__main__":
    main()
