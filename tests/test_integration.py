from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from risk_manager.config import MAPPINGS
from risk_manager.decision import DecisionEngine
from risk_manager.detector import generate_labeled_dataset, train_detector, Predictor
from risk_manager.demo import extract_detector_features
from risk_manager.features import FeatureEngine
from risk_manager.ingestion.csv_connector import CsvConnector
from risk_manager.ingestion.json_connector import JsonConnector
from risk_manager.models import Transaction
from risk_manager.pipeline import process_records
from risk_manager.responder import AutoResponder, MockActionAdapter
from risk_manager.verification import VerificationService

ROOT = Path(__file__).parents[1]


def test_full_pipeline_raw_csv_to_audit(tmp_path):
    """Integration test: Raw CSV -> Ingestion -> Normalization -> Features -> Detector -> Verifier -> Decision -> Responder -> Audit."""
    # 1. Raw CSV Ingestion & Normalization
    csv_file = tmp_path / "raw_merchant_a.csv"
    csv_file.write_text(
        "cust_id,order_id,order_total,pay_type,order_dt,currency,transaction_status\n"
        "C-TF-100,ORD-INT-100,350.00,credit card,2026-08-23T11:45:00Z,USD,completed\n"
    )

    connector = CsvConnector(csv_file)
    raw_records = connector.read()
    canonical_txns, stats = process_records(raw_records, MAPPINGS["merchant_a"], Transaction)

    assert stats.valid_records == 1
    txn = canonical_txns[0]
    assert txn.transaction_id == "ORD-INT-100"  # Mapping maps order_id to transaction_id for merchant_a
    assert txn.amount == Decimal("350.00")
    assert txn.payment_method == "CARD"

    # 2. Canonical Data & Feature Engine
    from data.synthetic.dataset_generator import create_synthetic_dataset
    customers, orders, txns, returns, chargebacks, devices, addresses = create_synthetic_dataset()
    feature_engine = FeatureEngine(
        transactions=txns + [txn],
        orders=orders,
        returns=returns,
        chargebacks=chargebacks,
        customers=customers,
        devices=devices,
        addresses=addresses,
        prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
    )

    # 3. Train & Predict Detector
    model_dir = tmp_path / "model"
    train_data = generate_labeled_dataset(num_samples=200, seed=42)
    train_detector(train_data, model_type="random_forest", test_size=0.2, val_size=0.2, seed=42, save_dir=model_dir)
    predictor = Predictor(model_dir=model_dir, model_version="detector-rf-1.0")

    features_dict = extract_detector_features(feature_engine, txn)
    detector_pred = predictor.predict(features_dict)
    assert detector_pred.case_type in {"return_abuse", "transaction_fraud", "fraud_spike", "abuse_ring", "normal"}
    assert 0.0 <= detector_pred.confidence <= 1.0

    # 4. Specialized Verification
    verifier_service = VerificationService(feature_engine=feature_engine, rule_version="1.0.0")
    verifier_result = verifier_service.verify(
        case_type="transaction_fraud",
        transaction=txn,
        detector_confidence=detector_pred.confidence,
    )
    assert verifier_result.verification_status in {"VERIFIED_SUSPICIOUS", "VERIFIED_NOT_SUSPICIOUS", "INCONCLUSIVE"}
    assert 0.0 <= verifier_result.risk_score <= 1.0
    assert verifier_result.explanation is not None

    # 5. Cost-Aware Decision Engine
    decision_engine = DecisionEngine.from_policy_file(ROOT / "config" / "merchant_policies.json")
    decision_result = decision_engine.decide(
        merchant_id="merchant_a",
        detector_result=detector_pred,
        verifier_result=verifier_result,
    )
    assert decision_result.decision in {"APPROVE", "MANUAL_REVIEW", "DEFENSIVE_ACTION"}
    assert "APPROVE" in decision_result.expected_loss_by_action

    # 6. Auto-Responder & Action Adapter Execution
    responder = AutoResponder.from_config(template_file=ROOT / "config" / "response_templates.json")
    response_result = responder.respond(
        decision_result=decision_result,
        event_id=txn.transaction_id,
        input_source="merchant_a_csv",
    )
    assert response_result.action.action_code != ""

    adapter = MockActionAdapter(mode="test")
    receipt = adapter.execute(response_result)
    assert receipt.status == "SUCCESS"
    assert receipt.simulated is True

    # 7. Audit Log Traceability
    audit_records = responder.audit_logger.get_by_event_id(txn.transaction_id)
    assert len(audit_records) >= 1
    latest_audit = audit_records[-1]
    assert latest_audit.audit_id.startswith("aud_")
    assert latest_audit.decision == decision_result.decision


def test_ui_evaluate_single_transaction_pipeline_routing():
    from app import evaluate_single_transaction
    from risk_manager.models import Transaction
    from datetime import datetime, timezone
    from decimal import Decimal

    txn = Transaction(
        transaction_id="ORD-UI-TEST-100",
        order_id="ORD-UI-TEST-100",
        customer_id="C-UI-100",
        amount=Decimal("150.00"),
        currency="USD",
        payment_method="UPI",
        transaction_status="COMPLETED",
        timestamp=datetime.now(timezone.utc),
    )
    result = evaluate_single_transaction(txn, merchant_id="merchant_a")
    assert result["transaction_id"] == "ORD-UI-TEST-100"
    assert result["customer_id"] == "C-UI-100"
    assert result["merchant_id"] == "merchant_a"
    assert result["case_type"] in {"normal", "return_abuse", "transaction_fraud", "fraud_spike", "abuse_ring"}
    assert 0.0 <= result["detector_confidence"] <= 1.0
    assert result["decision"] in {"APPROVE", "MANUAL_REVIEW", "DEFENSIVE_ACTION"}
    assert result["audit_id"].startswith("aud_")
