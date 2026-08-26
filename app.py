import json
import io
import csv
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
from typing import Any

import streamlit as st

from data.synthetic.dataset_generator import create_synthetic_dataset
from risk_manager.config import MAPPINGS
from risk_manager.decision import DecisionEngine
from risk_manager.detector import generate_labeled_dataset, train_detector, Predictor
from risk_manager.demo import extract_detector_features, run_demo_pipeline
from risk_manager.features import FeatureEngine
from risk_manager.ingestion.csv_connector import CsvConnector
from risk_manager.ingestion.json_connector import JsonConnector
from risk_manager.models import Transaction
from risk_manager.normalize import detect_merchant_schema
from risk_manager.pipeline import process_records, ingest_raw_data
from risk_manager.responder import AutoResponder, MockActionAdapter
from risk_manager.verification import VerificationService
from risk_manager.verification.types import VerificationResult, ModelExplanation
from risk_manager.security import (
    validate_file_upload,
    sanitize_display_text,
)

ROOT = Path(__file__).parent

st.set_page_config(
    page_title="AI Risk Manager — Defensive Risk Pipeline",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ AI Risk Manager — Defensive Risk Pipeline")
st.markdown("A defense-only, production-oriented risk classification, verification, decision, and auto-responder platform.")

@st.cache_resource
def load_pipeline():
    customers, orders, txns, returns, chargebacks, devices, addresses = create_synthetic_dataset()
    feature_engine = FeatureEngine(
        transactions=txns,
        orders=orders,
        returns=returns,
        chargebacks=chargebacks,
        customers=customers,
        devices=devices,
        addresses=addresses,
        prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
    )
    tmp_dir = tempfile.TemporaryDirectory()
    model_path = Path(tmp_dir.name)
    train_data = generate_labeled_dataset(num_samples=300, seed=42)
    train_detector(
        train_data,
        model_type="random_forest",
        test_size=0.2,
        val_size=0.2,
        seed=42,
        save_dir=model_path,
    )
    detector_predictor = Predictor(model_dir=model_path, model_version="detector-rf-1.0")
    verifier_service = VerificationService(feature_engine=feature_engine, rule_version="1.0.0")
    decision_engine = DecisionEngine.from_policy_file(ROOT / "config" / "merchant_policies.json")
    responder = AutoResponder.from_config(template_file=ROOT / "config" / "response_templates.json")
    action_adapter = MockActionAdapter(mode="defense_only_simulation")
    return feature_engine, detector_predictor, verifier_service, decision_engine, responder, action_adapter

@st.cache_data
def get_demo_results():
    return run_demo_pipeline(verbose=False)

def evaluate_single_transaction(txn: Transaction, merchant_id: str):
    feature_engine, detector_predictor, verifier_service, decision_engine, responder, action_adapter = load_pipeline()
    feature_engine.transactions[txn.transaction_id] = txn

    features_dict = extract_detector_features(feature_engine, txn)
    detector_pred = detector_predictor.predict(features_dict)
    detected_case = detector_pred.case_type

    if detected_case == "normal":
        verifier_result = VerificationResult(
            case_type="normal",
            verifier_name="LegitimateControlBaseline",
            verification_status="VERIFIED_NOT_SUSPICIOUS",
            risk_score=0.0,
            confidence=0.99,
            evidence={},
            reasons=["Control baseline transaction has zero risk indicators."],
            applicable_rules=[],
            ml_evidence={},
            historical_evidence={},
            explanation=ModelExplanation(
                method="unavailable",
                available=False,
                top_features=[{"feature": "baseline_control", "contribution": 0.0, "value": 0.0}],
                base_value=0.0,
                model_output=0.0,
                note="Baseline control transaction",
            ),
            model_version="1.0.0",
            rule_version="1.0.0",
            edge_flags=[],
            timestamp=VerificationResult.now_iso(),
        )
    else:
        verifier_case = detected_case if detected_case in verifier_service._verifiers else "transaction_fraud"
        verifier_result = verifier_service.verify(
            case_type=verifier_case,
            transaction=txn,
            detector_confidence=detector_pred.confidence,
        )

    decision_result = decision_engine.decide(
        merchant_id=merchant_id,
        detector_result=detector_pred,
        verifier_result=verifier_result,
    )

    response_result = responder.respond(
        decision_result=decision_result,
        event_id=txn.transaction_id,
        input_source=f"{merchant_id}_ui",
    )

    execution_receipt = action_adapter.execute(response_result)
    audit_records = responder.audit_logger.get_by_event_id(txn.transaction_id)
    latest_audit = audit_records[-1] if audit_records else None

    shap_top_features = [
        {
            "feature": f.get("feature", "unknown"),
            "contribution": round(float(f.get("contribution", f.get("abs_contribution", 0.0))), 4),
            "value": round(float(f.get("value", 0.0)), 2),
        }
        for f in (verifier_result.explanation.top_features if verifier_result.explanation else [])
    ]

    return {
        "transaction_id": txn.transaction_id,
        "customer_id": txn.customer_id,
        "merchant_id": merchant_id,
        "scenario_name": detected_case,
        "case_type": detected_case,
        "amount": float(txn.amount),
        "detector_confidence": detector_pred.confidence,
        "verifier_status": verifier_result.verification_status,
        "verifier_risk_score": verifier_result.risk_score,
        "shap_top_features": shap_top_features,
        "decision": decision_result.decision,
        "expected_loss_by_action": decision_result.expected_loss_by_action,
        "response_action_code": response_result.action.action_code,
        "response_action_type": response_result.action.action_type,
        "response_message": response_result.action.message,
        "mock_execution_status": execution_receipt.status,
        "mock_executed_steps": execution_receipt.executed_steps,
        "audit_id": latest_audit.audit_id if latest_audit else "",
    }

def render_detailed_results(res: dict):
    st.subheader(f"Input Event: {res['scenario_name'].replace('_', ' ').title()}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Merchant ID", res["merchant_id"].upper())
    c2.metric("Transaction ID", res["transaction_id"])
    c3.metric("Amount", f"${res['amount']:.2f}")
    c4.metric("Risk Class Target", res["scenario_name"].upper())

    st.divider()

    col_detector, col_verifier = st.columns(2)

    with col_detector:
        st.markdown("### 1. 4-Class Case Detector")
        st.info(f"**Predicted Case Type:** `{res['case_type']}`")
        st.metric("Detector Confidence", f"{res['detector_confidence'] * 100:.1f}%")

    with col_verifier:
        st.markdown("### 2. Specialized Verifier")
        status = res["verifier_status"]
        if status == "VERIFIED_SUSPICIOUS":
            st.error(f"**Status:** {status}")
        elif status == "VERIFIED_NOT_SUSPICIOUS":
            st.success(f"**Status:** {status}")
        else:
            st.warning(f"**Status:** {status}")
        st.metric("Verifier Risk Score", f"{res['verifier_risk_score']:.3f}")

    st.divider()

    col_shap, col_decision = st.columns(2)

    with col_shap:
        st.markdown("### 3. SHAP Top Feature Contributions")
        top_feats = res.get("shap_top_features", [])
        if top_feats:
            st.table(top_feats)
        else:
            st.write("No feature explanation available.")

    with col_decision:
        st.markdown("### 4. Cost-Aware Decision Engine")
        dec = res["decision"]
        if dec == "APPROVE":
            st.success(f"**Decision Output:** {dec}")
        elif dec == "DEFENSIVE_ACTION":
            st.error(f"**Decision Output:** {dec}")
        else:
            st.warning(f"**Decision Output:** {dec}")

        st.markdown("**Expected Loss by Action:**")
        loss_cols = st.columns(3)
        exp_losses = res["expected_loss_by_action"]
        loss_cols[0].metric("APPROVE", f"${exp_losses.get('APPROVE', 0.0):.2f}")
        loss_cols[1].metric("MANUAL_REVIEW", f"${exp_losses.get('MANUAL_REVIEW', 0.0):.2f}")
        loss_cols[2].metric("DEFENSIVE_ACTION", f"${exp_losses.get('DEFENSIVE_ACTION', 0.0):.2f}")

    st.divider()

    col_responder, col_audit = st.columns(2)

    with col_responder:
        st.markdown("### 5. Auto-Responder & Action Execution")
        st.write(f"**Action Code:** `{res['response_action_code']}`")
        st.write(f"**Action Type:** `{res['response_action_type']}`")
        st.info(f"**Defensive Message:** {res['response_message']}")
        st.markdown("**Mock Executed Steps:**")
        for step in res["mock_executed_steps"]:
            st.write(f"- {step}")

    with col_audit:
        st.markdown("### 6. Audit Logging & Traceability")
        st.write(f"**Audit ID:** `{res['audit_id']}`")
        st.write(f"**Mock Status:** `{res['mock_execution_status']}`")
        st.write("**Model Versions:** Detector `detector-rf-1.0` | Verifier `1.0.0`")
        st.write("**Policy Version:** `1.0.0`")

st.sidebar.header("Input Data Mode")
input_mode = st.sidebar.radio(
    "Select Input Method:",
    [
        "Unified Input (File / Text Paste)",
        "Demo Scenarios",
        "Sample Merchant Dataset",
        "Simulated Event Generator",
    ]
)

selected_scenario = None

if input_mode == "Unified Input (File / Text Paste)":
    st.sidebar.subheader("Unified Input")
    uploaded_file = st.sidebar.file_uploader("Upload CSV or JSON File", type=["csv", "json", "txt"])
    pasted_text = st.sidebar.text_area("Or Paste CSV / JSON Data:", height=150, help="Paste raw CSV text or JSON object/array here.")

    user_input = None
    if uploaded_file is not None:
        user_input = uploaded_file.getvalue()
    elif pasted_text.strip():
        user_input = pasted_text.strip()

    if user_input is not None:
        input_bytes = user_input if isinstance(user_input, bytes) else user_input.encode("utf-8")
        filename = uploaded_file.name if uploaded_file is not None else "pasted_data.json"
        is_valid_upload, upload_err = validate_file_upload(input_bytes, filename)
        
        if not is_valid_upload:
            st.error(f"Security / Validation Error: {upload_err}")
        else:
            valid_txns, stats, merchant_id, format_detected = ingest_raw_data(user_input)
            
            st.markdown(f"### 📥 M1 Ingestion & Validation Statistics (Format: `{format_detected.upper()}`, Schema: `{merchant_id.upper()}`)")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Total Records", stats.total_records)
            s2.metric("Valid Records", stats.valid_records)
            s3.metric("Invalid Records", stats.invalid_records)
            s4.metric("Duplicate Records", stats.duplicate_records)

            if stats.errors:
                with st.expander("⚠️ Validation Warnings / Quarantined Error Details", expanded=True):
                    for err in stats.errors:
                        st.warning(sanitize_display_text(err))

            if valid_txns:
                run_analysis = st.button("🚀 Run Risk Analysis on Validated Records", type="primary")
                if run_analysis or st.session_state.get("run_batch_analysis", False):
                    st.session_state["run_batch_analysis"] = True
                    with st.spinner("Processing valid transactions through M1–M9 Risk Pipeline..."):
                        batch_results = [evaluate_single_transaction(t, merchant_id) for t in valid_txns]

                    st.markdown("### 📊 Pipeline Analysis Results Summary")
                    summary_table = [
                        {
                            "Transaction ID": r["transaction_id"],
                            "Customer ID": r["customer_id"],
                            "Amount ($)": f"${r['amount']:.2f}",
                            "Detector Class": r["case_type"],
                            "Confidence": f"{r['detector_confidence'] * 100:.1f}%",
                            "Verifier Status": r["verifier_status"],
                            "Verifier Score": f"{r['verifier_risk_score']:.3f}",
                            "Decision": r["decision"],
                            "Action Code": r["response_action_code"],
                            "Audit ID": r["audit_id"],
                        }
                        for r in batch_results
                    ]
                    st.dataframe(summary_table, use_container_width=True)

                    st.markdown("### 🔍 Detailed Per-Transaction Pipeline Breakdown")
                    txn_map = {f"{r['transaction_id']} (Customer: {r['customer_id']})": r for r in batch_results}
                    selected_txn_label = st.selectbox("Select Transaction to Inspect Detail:", list(txn_map.keys()))
                    selected_scenario = txn_map[selected_txn_label]
            else:
                st.error("No valid canonical records available to send to the risk pipeline.")

elif input_mode == "Demo Scenarios":
    results = get_demo_results()
    scenario_map = {
        f"Scenario {r['scenario_idx']}: {r['scenario_name'].replace('_', ' ').title()} ({r['transaction_id']})": r
        for r in results
    }
    selected_scenario_key = st.sidebar.selectbox("Select Test Scenario:", list(scenario_map.keys()))
    selected_scenario = scenario_map[selected_scenario_key]

elif input_mode == "Sample Merchant Dataset":
    st.sidebar.subheader("Sample Selection")
    sample_choice = st.sidebar.selectbox(
        "Select Synthetic Dataset:",
        [
            ("merchant_a_20", "data/synthetic/merchant_a_20.csv"),
            ("merchant_b_20", "data/synthetic/merchant_b_20.json"),
            ("merchant_a", "data/synthetic/merchant_a.csv"),
            ("merchant_b", "data/synthetic/merchant_b.json"),
        ],
        format_func=lambda x: f"{x[0].upper()} ({x[1]})"
    )
    sample_key, file_path = sample_choice
    path = ROOT / file_path
    
    if path.exists():
        valid_txns, stats, merchant_id, format_detected = ingest_raw_data(path.read_bytes())

        st.markdown(f"### 📥 M1 Ingestion & Validation Statistics (Format: `{format_detected.upper()}`, Schema: `{merchant_id.upper()}`)")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Total Records", stats.total_records)
        s2.metric("Valid Records", stats.valid_records)
        s3.metric("Invalid Records", stats.invalid_records)
        s4.metric("Duplicate Records", stats.duplicate_records)

        if stats.errors:
            with st.expander("⚠️ Validation Warnings / Errors", expanded=True):
                for err in stats.errors:
                    st.warning(sanitize_display_text(err))

        if valid_txns:
            run_analysis = st.button("🚀 Run Risk Analysis", type="primary")
            if run_analysis or st.session_state.get("run_sample_analysis", False):
                st.session_state["run_sample_analysis"] = True
                batch_results = [evaluate_single_transaction(t, merchant_id) for t in valid_txns]
                summary_table = [
                    {
                        "Transaction ID": r["transaction_id"],
                        "Customer ID": r["customer_id"],
                        "Amount ($)": f"${r['amount']:.2f}",
                        "Detector Class": r["case_type"],
                        "Confidence": f"{r['detector_confidence'] * 100:.1f}%",
                        "Verifier Status": r["verifier_status"],
                        "Verifier Score": f"{r['verifier_risk_score']:.3f}",
                        "Decision": r["decision"],
                        "Action Code": r["response_action_code"],
                        "Audit ID": r["audit_id"],
                    }
                    for r in batch_results
                ]
                st.dataframe(summary_table, use_container_width=True)
                txn_map = {f"{r['transaction_id']} (Customer: {r['customer_id']})": r for r in batch_results}
                selected_txn_label = st.selectbox("Select Transaction to Inspect Detail:", list(txn_map.keys()))
                selected_scenario = txn_map[selected_txn_label]

elif input_mode == "Simulated Event Generator":
    st.sidebar.subheader("Event Parameters")
    cust_id = st.sidebar.text_input("Customer ID:", "C-TF-100")
    order_id = st.sidebar.text_input("Order / Transaction ID:", "TXN-SIM-500")
    amount = st.sidebar.number_input("Transaction Amount ($):", min_value=0.01, value=350.00, step=10.0)
    pay_method = st.sidebar.selectbox("Payment Method:", ["card", "upi", "wallet", "credit card"])
    txn_status = st.sidebar.selectbox("Transaction Status:", ["completed", "pending", "settled"])
    
    raw_event = [{
        "cust_id": cust_id,
        "order_id": order_id,
        "order_total": str(amount),
        "pay_type": pay_method,
        "order_dt": datetime.now(timezone.utc).isoformat(),
        "currency": "USD",
        "transaction_status": txn_status,
    }]

    valid_txns, stats, merchant_id, format_detected = ingest_raw_data(raw_event)
    
    st.markdown(f"### 📥 M1 Ingestion & Validation Statistics (Schema: `{merchant_id.upper()}`)")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Records", stats.total_records)
    s2.metric("Valid Records", stats.valid_records)
    s3.metric("Invalid Records", stats.invalid_records)
    s4.metric("Duplicate Records", stats.duplicate_records)

    if stats.errors:
        with st.expander("⚠️ Validation Warnings / Errors", expanded=True):
            for err in stats.errors:
                st.warning(sanitize_display_text(err))

    if valid_txns:
        run_sim = st.button("🚀 Run Risk Analysis", type="primary")
        if run_sim or st.session_state.get("run_sim_analysis", False):
            st.session_state["run_sim_analysis"] = True
            selected_scenario = evaluate_single_transaction(valid_txns[0], merchant_id)

if selected_scenario is not None:
    render_detailed_results(selected_scenario)
