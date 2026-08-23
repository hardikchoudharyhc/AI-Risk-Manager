MAPPINGS = {
    "merchant_a": {
        "cust_id": "customer_id", "order_id": "order_id", "order_total": "amount",
        "pay_type": "payment_method", "order_dt": "timestamp", "currency": "currency",
        "transaction_status": "transaction_status",
    },
    "merchant_b": {
        "customerId": "customer_id", "orderId": "order_id", "amount": "amount",
        "paymentMethod": "payment_method", "timestamp": "timestamp", "currency": "currency",
        "transactionStatus": "transaction_status",
    },
    "merchant_c": {
        "user_id": "customer_id", "order_ref": "order_id", "transaction_value": "amount",
        "payment": "payment_method", "date": "timestamp", "currency_code": "currency",
        "status": "transaction_status",
    },
}