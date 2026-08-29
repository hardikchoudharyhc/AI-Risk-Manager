from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class MockRazorpayProvider:
    """Mock Razorpay API provider delivering 20 deterministic realistic payments for testing."""

    @staticmethod
    def get_mock_payments() -> list[dict[str, Any]]:
        base_ts = int(datetime(2026, 8, 28, 10, 0, 0, tzinfo=timezone.utc).timestamp())
        
        # 20 realistic payment records with varied payment methods, statuses, and risk profiles
        records = [
            # 1. Low risk standard UPI payment
            {
                "id": "pay_RZP_MOCK_101",
                "entity": "payment",
                "amount": 15000,  # 150.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_101",
                "customer_id": "cust_RZP_101",
                "method": "upi",
                "email": "priya.sharma@example.com",
                "contact": "+919876543210",
                "created_at": base_ts - 3600 * 1,
            },
            # 2. Standard Card payment
            {
                "id": "pay_RZP_MOCK_102",
                "entity": "payment",
                "amount": 45000,  # 450.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_102",
                "customer_id": "cust_RZP_102",
                "method": "card",
                "email": "rohit.verma@example.com",
                "contact": "+919876543211",
                "created_at": base_ts - 3600 * 2,
            },
            # 3. Higher value card payment
            {
                "id": "pay_RZP_MOCK_103",
                "entity": "payment",
                "amount": 1250000,  # 12,500.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_103",
                "customer_id": "cust_RZP_103",
                "method": "card",
                "email": "ananya.rao@example.com",
                "contact": "+919876543212",
                "created_at": base_ts - 3600 * 3,
            },
            # 4. Failed card attempt
            {
                "id": "pay_RZP_MOCK_104",
                "entity": "payment",
                "amount": 35000,  # 350.00 INR
                "currency": "INR",
                "status": "failed",
                "order_id": "order_RZP_MOCK_104",
                "customer_id": "cust_RZP_104",
                "method": "card",
                "email": "vikram.singh@example.com",
                "contact": "+919876543213",
                "created_at": base_ts - 3600 * 4,
            },
            # 5. Netbanking authorized payment
            {
                "id": "pay_RZP_MOCK_105",
                "entity": "payment",
                "amount": 88000,  # 880.00 INR
                "currency": "INR",
                "status": "authorized",
                "order_id": "order_RZP_MOCK_105",
                "customer_id": "cust_RZP_105",
                "method": "netbanking",
                "email": "neha.gupta@example.com",
                "contact": "+919876543214",
                "created_at": base_ts - 3600 * 5,
            },
            # 6. Return Abuse pattern candidate
            {
                "id": "pay_RZP_MOCK_106",
                "entity": "payment",
                "amount": 899000,  # 8,990.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_106",
                "customer_id": "C-RA-100",
                "method": "card",
                "email": "return.abuser@example.com",
                "contact": "+919876543215",
                "created_at": base_ts - 3600 * 6,
            },
            # 7. Transaction Fraud pattern candidate (extreme high amount)
            {
                "id": "pay_RZP_MOCK_107",
                "entity": "payment",
                "amount": 4999900,  # 49,999.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_107",
                "customer_id": "C-TF-100",
                "method": "card",
                "email": "suspicious.carder@example.com",
                "contact": "+919876543216",
                "created_at": base_ts - 3600 * 7,
            },
            # 8. Fraud Spike anomaly candidate
            {
                "id": "pay_RZP_MOCK_108",
                "entity": "payment",
                "amount": 3500000,  # 35,000.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_108",
                "customer_id": "C-FS-100",
                "method": "card",
                "email": "spike.user@example.com",
                "contact": "+919876543217",
                "created_at": base_ts - 3600 * 8,
            },
            # 9. Abuse Ring connected entity candidate
            {
                "id": "pay_RZP_MOCK_109",
                "entity": "payment",
                "amount": 1200000,  # 12,000.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_109",
                "customer_id": "C-RING-100",
                "method": "upi",
                "email": "ring.leader@example.com",
                "contact": "+919876543218",
                "created_at": base_ts - 3600 * 9,
            },
            # 10. Wallet payment
            {
                "id": "pay_RZP_MOCK_110",
                "entity": "payment",
                "amount": 25000,  # 250.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_110",
                "customer_id": "cust_RZP_110",
                "method": "wallet",
                "email": "karan.mehta@example.com",
                "contact": "+919876543219",
                "created_at": base_ts - 3600 * 10,
            },
            # 11. Low amount UPI payment
            {
                "id": "pay_RZP_MOCK_111",
                "entity": "payment",
                "amount": 9900,  # 99.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_111",
                "customer_id": "cust_RZP_111",
                "method": "upi",
                "email": "deepak.kumar@example.com",
                "contact": "+919876543220",
                "created_at": base_ts - 3600 * 11,
            },
            # 12. Mid-range Card payment
            {
                "id": "pay_RZP_MOCK_112",
                "entity": "payment",
                "amount": 149900,  # 1,499.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_112",
                "customer_id": "cust_RZP_112",
                "method": "card",
                "email": "simran.kaur@example.com",
                "contact": "+919876543221",
                "created_at": base_ts - 3600 * 12,
            },
            # 13. Failed netbanking attempt
            {
                "id": "pay_RZP_MOCK_113",
                "entity": "payment",
                "amount": 62000,  # 620.00 INR
                "currency": "INR",
                "status": "failed",
                "order_id": "order_RZP_MOCK_113",
                "customer_id": "cust_RZP_113",
                "method": "netbanking",
                "email": "rahul.jain@example.com",
                "contact": "+919876543222",
                "created_at": base_ts - 3600 * 13,
            },
            # 14. Standard UPI purchase
            {
                "id": "pay_RZP_MOCK_114",
                "entity": "payment",
                "amount": 39900,  # 399.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_114",
                "customer_id": "cust_RZP_114",
                "method": "upi",
                "email": "pooja.nair@example.com",
                "contact": "+919876543223",
                "created_at": base_ts - 3600 * 14,
            },
            # 15. Electronic item card purchase
            {
                "id": "pay_RZP_MOCK_115",
                "entity": "payment",
                "amount": 2999900,  # 29,999.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_115",
                "customer_id": "cust_RZP_115",
                "method": "card",
                "email": "sanjay.deshmukh@example.com",
                "contact": "+919876543224",
                "created_at": base_ts - 3600 * 15,
            },
            # 16. Fast repeat UPI payment
            {
                "id": "pay_RZP_MOCK_116",
                "entity": "payment",
                "amount": 19900,  # 199.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_116",
                "customer_id": "cust_RZP_116",
                "method": "upi",
                "email": "tanvi.patel@example.com",
                "contact": "+919876543225",
                "created_at": base_ts - 3600 * 16,
            },
            # 17. Wallet refund/failed case
            {
                "id": "pay_RZP_MOCK_117",
                "entity": "payment",
                "amount": 75000,  # 750.00 INR
                "currency": "INR",
                "status": "failed",
                "order_id": "order_RZP_MOCK_117",
                "customer_id": "cust_RZP_117",
                "method": "wallet",
                "email": "amit.chopra@example.com",
                "contact": "+919876543226",
                "created_at": base_ts - 3600 * 17,
            },
            # 18. High velocity UPI payment
            {
                "id": "pay_RZP_MOCK_118",
                "entity": "payment",
                "amount": 159900,  # 1,599.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_118",
                "customer_id": "cust_RZP_118",
                "method": "upi",
                "email": "divya.reddy@example.com",
                "contact": "+919876543227",
                "created_at": base_ts - 3600 * 18,
            },
            # 19. Large order payment
            {
                "id": "pay_RZP_MOCK_119",
                "entity": "payment",
                "amount": 4500000,  # 45,000.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_119",
                "customer_id": "cust_RZP_119",
                "method": "card",
                "email": "arjun.kapoor@example.com",
                "contact": "+919876543228",
                "created_at": base_ts - 3600 * 19,
            },
            # 20. Netbanking completed transaction
            {
                "id": "pay_RZP_MOCK_120",
                "entity": "payment",
                "amount": 185000,  # 1,850.00 INR
                "currency": "INR",
                "status": "captured",
                "order_id": "order_RZP_MOCK_120",
                "customer_id": "cust_RZP_120",
                "method": "netbanking",
                "email": "meera.joshi@example.com",
                "contact": "+919876543229",
                "created_at": base_ts - 3600 * 20,
            },
        ]
        return records

    @staticmethod
    def send_risk_result(risk_result: dict[str, Any]) -> dict[str, Any]:
        """Simulate outbound risk result receipt by mock Razorpay platform."""
        txn_id = risk_result.get("transaction_id", "unknown_txn")
        risk_level = risk_result.get("risk_level") or risk_result.get("risk_assessment", {}).get("risk_level", "MEDIUM")
        decision = risk_result.get("decision", "APPROVED")
        action = risk_result.get("response_action_code") or risk_result.get("response", {}).get("action_code", "APPROVE")

        return {
            "success": True,
            "provider": "razorpay",
            "mode": "mock",
            "transaction_id": str(txn_id),
            "risk_status": str(risk_level),
            "decision": str(decision),
            "action": str(action),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Risk result received by mock Razorpay",
        }
