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
    page_title="AI Risk Manager — Defensive Risk Intelligence Platform",
    page_icon="📊",
    layout="wide"
)

# Enterprise Dashboard Custom CSS
st.markdown("""
<style>
    /* Global Background & Typography */
    .stApp {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    header[data-testid="stHeader"] {
        background-color: #F8FAFC !important;
    }

    /* Main Container Padding */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    /* Header Banner */
    .enterprise-header {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
    }
    .enterprise-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0;
        line-height: 1.2;
    }
    .enterprise-subtitle {
        font-size: 0.875rem;
        font-weight: 600;
        color: #1D4ED8;
        margin-top: 0.25rem;
    }
    .enterprise-caption {
        font-size: 0.775rem;
        color: #475569;
        margin-top: 0.15rem;
    }

    /* Status Tracker */
    .tracker-container {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin-bottom: 1.25rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .tracker-item {
        font-size: 0.8rem;
        font-weight: 600;
        color: #15803D;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    /* Cards & Containers */
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 0.85rem 1rem;
        text-align: left;
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-val {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0F172A;
        margin-top: 0.15rem;
    }

    /* Demo Badge */
    .demo-badge {
        background-color: #FEF3C7;
        color: #B45309;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-block;
        margin-bottom: 0.5rem;
    }

    /* Hide redundant elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


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

    # Map Risk Level
    risk_score = verifier_result.risk_score
    if detected_case == "normal" or risk_score < 0.25:
        risk_level = "LOW"
    elif risk_score < 0.60:
        risk_level = "MEDIUM"
    elif risk_score < 0.85:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    # Human-readable decision summary
    dec = decision_result.decision
    exp_losses = decision_result.expected_loss_by_action
    if dec == "MANUAL_REVIEW":
        human_expl = f"Manual review selected because the estimated loss of approval (${exp_losses.get('APPROVE', 0.0):.2f}) exceeds the expected cost of review (${exp_losses.get('MANUAL_REVIEW', 0.0):.2f})."
    elif dec == "DEFENSIVE_ACTION":
        human_expl = f"Defensive action selected because the risk score ({risk_score:.2f}) and verified suspicious indicators exceed safety thresholds."
    else:
        human_expl = f"Transaction approved as expected loss (${exp_losses.get('APPROVE', 0.0):.2f}) is within acceptable merchant policy limits."

    return {
        "transaction_id": txn.transaction_id,
        "order_id": txn.order_id,
        "customer_id": txn.customer_id,
        "merchant_id": merchant_id,
        "currency": txn.currency,
        "payment_method": txn.payment_method,
        "timestamp": txn.timestamp.isoformat(),
        "transaction_status": txn.transaction_status,
        "scenario_name": detected_case,
        "case_type": detected_case,
        "amount": float(txn.amount),
        "detector_confidence": detector_pred.confidence,
        "verifier_status": verifier_result.verification_status,
        "verifier_risk_score": verifier_result.risk_score,
        "risk_level": risk_level,
        "shap_top_features": shap_top_features,
        "decision": decision_result.decision,
        "expected_loss_by_action": exp_losses,
        "human_explanation": human_expl,
        "response_action_code": response_result.action.action_code,
        "response_action_type": response_result.action.action_type,
        "response_message": response_result.action.message,
        "mock_execution_status": execution_receipt.status,
        "mock_executed_steps": execution_receipt.executed_steps,
        "audit_id": latest_audit.audit_id if latest_audit else "",
    }


def render_pipeline_tracker():
    st.markdown("""
    <div class="tracker-container">
        <span class="tracker-item">Input ✓</span>
        <span style="color:#CBD5E1;">—</span>
        <span class="tracker-item">Validation ✓</span>
        <span style="color:#CBD5E1;">—</span>
        <span class="tracker-item">Detection ✓</span>
        <span style="color:#CBD5E1;">—</span>
        <span class="tracker-item">Verification ✓</span>
        <span style="color:#CBD5E1;">—</span>
        <span class="tracker-item">Explainability ✓</span>
        <span style="color:#CBD5E1;">—</span>
        <span class="tracker-item">Decision ✓</span>
        <span style="color:#CBD5E1;">—</span>
        <span class="tracker-item">Response ✓</span>
        <span style="color:#CBD5E1;">—</span>
        <span class="tracker-item">Audit ✓</span>
    </div>
    """, unsafe_allow_html=True)


def render_transaction_detail(res: dict):
    st.markdown("### Transaction Analysis & Risk Detail")

    # 1. Transaction Info Grid
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Transaction ID", res["transaction_id"])
    d2.metric("Customer ID", res["customer_id"])
    d3.metric("Amount", f"${res['amount']:.2f} {res['currency']}")
    d4.metric("Risk Level", res["risk_level"])

    st.markdown("---")

    col_info, col_risk = st.columns(2)

    with col_info:
        st.markdown("#### Transaction Information")
        info_table = [
            {"Property": "Order ID", "Value": res["order_id"]},
            {"Property": "Payment Method", "Value": res["payment_method"]},
            {"Property": "Timestamp", "Value": res["timestamp"]},
            {"Property": "Transaction Status", "Value": res["transaction_status"]},
            {"Property": "Merchant Schema", "Value": res["merchant_id"].upper()},
        ]
        st.dataframe(info_table, use_container_width=True, hide_index=True)

    with col_risk:
        st.markdown("#### Risk Assessment")
        risk_table = [
            {"Metric": "Detected Case Type", "Value": res["case_type"]},
            {"Metric": "Detector Confidence", "Value": f"{res['detector_confidence'] * 100:.1f}%"},
            {"Metric": "Verifier Status", "Value": res["verifier_status"]},
            {"Metric": "Verifier Risk Score", "Value": f"{res['verifier_risk_score']:.3f}"},
        ]
        st.dataframe(risk_table, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 2. SHAP & Decision Engine
    col_shap, col_decision = st.columns(2)

    with col_shap:
        st.markdown("#### Why was this flagged?")
        st.caption("SHAP Top Contributing Feature Attribution")
        top_feats = res.get("shap_top_features", [])
        if top_feats:
            st.dataframe(top_feats, use_container_width=True, hide_index=True)
        else:
            st.info("No suspicious feature contributions detected for this baseline transaction.")

    with col_decision:
        st.markdown("#### Recommended Decision")
        st.write(f"**Decision Output:** `{res['decision']}`")
        st.caption(res["human_explanation"])

        st.markdown("**Expected Loss Evaluation ($):**")
        exp_losses = res["expected_loss_by_action"]
        l1, l2, l3 = st.columns(3)
        l1.metric("Approve", f"${exp_losses.get('APPROVE', 0.0):.2f}")
        l2.metric("Manual Review", f"${exp_losses.get('MANUAL_REVIEW', 0.0):.2f}")
        l3.metric("Defensive Action", f"${exp_losses.get('DEFENSIVE_ACTION', 0.0):.2f}")

    st.markdown("---")

    # 3. Auto-Responder & Audit
    col_resp, col_audit = st.columns(2)

    with col_resp:
        st.markdown("#### Response Action")
        st.write(f"**Action Code:** `{res['response_action_code']}`")
        st.write(f"**Action Type:** `{res['response_action_type']}`")
        st.info(f"**Message:** {res['response_message']}")
        st.markdown("**Executed Steps Checklist:**")
        for step in res["mock_executed_steps"]:
            st.write(f"- [x] {step}")

    with col_audit:
        st.markdown("#### Audit & Compliance Panel")
        audit_table = [
            {"Property": "Audit ID", "Value": res["audit_id"]},
            {"Property": "Execution Status", "Value": res["mock_execution_status"]},
            {"Property": "Detector Version", "Value": "detector-rf-1.0"},
            {"Property": "Verifier Version", "Value": "1.0.0"},
            {"Property": "Policy Version", "Value": "1.0.0"},
        ]
        st.dataframe(audit_table, use_container_width=True, hide_index=True)

    with st.expander("Technical Details", expanded=False):
        st.json(res)


# Top Banner Header
st.markdown("""
<div class="enterprise-header">
    <div class="enterprise-title">AI Risk Manager</div>
    <div class="enterprise-subtitle">Defensive Risk Intelligence Platform</div>
    <div class="enterprise-caption">Transaction risk detection, verification and decision support</div>
</div>
""", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.markdown("### AI Risk Manager")
nav_choice = st.sidebar.radio(
    "Navigation:",
    [
        "Risk Analysis",
        "Integrations",
        "Transactions",
        "Input Data",
        "Audit Trail",
        "Demo / Test Data",
    ]
)

# Session state initialization
if "batch_results" not in st.session_state:
    st.session_state["batch_results"] = []
if "stats" not in st.session_state:
    st.session_state["stats"] = None
if "merchant_id" not in st.session_state:
    st.session_state["merchant_id"] = "canonical"
if "format_detected" not in st.session_state:
    st.session_state["format_detected"] = "unknown"

# NAVIGATION ROUTING

if nav_choice == "Input Data" or nav_choice == "Risk Analysis":
    st.subheader("Analyze Transactions")
    st.caption("Upload transaction data or paste records for risk analysis.")

    uploaded_file = st.file_uploader("Upload CSV or JSON File", type=["csv", "json", "txt"], help="Supported: CSV and JSON formatted datasets.")
    pasted_text = st.text_area("Or Paste CSV / JSON Data:", height=120, help="Paste raw CSV text or JSON array/object here.")

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
            st.error(f"Input Validation Error: {upload_err}")
        else:
            valid_txns, stats, merchant_id, format_detected = ingest_raw_data(user_input)
            st.session_state["stats"] = stats
            st.session_state["merchant_id"] = merchant_id
            st.session_state["format_detected"] = format_detected

            # Compact Ingestion Status Bar
            st.markdown(f"**Ingestion Status:** Format `{format_detected.upper()}` | Schema `{merchant_id.upper()}`")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Total Records", stats.total_records)
            s2.metric("Valid Records", stats.valid_records)
            s3.metric("Rejected Records", stats.invalid_records)
            s4.metric("Duplicate Records", stats.duplicate_records)

            if stats.errors:
                st.markdown("#### Input Validation Warnings")
                st.write(f"{stats.total_records} records received | {stats.valid_records} accepted | {stats.invalid_records} rejected")
                with st.expander("View Rejected Record Details", expanded=False):
                    for idx, err in enumerate(stats.errors, start=1):
                        st.write(f"**Row {idx}:** {sanitize_display_text(err)}")

                with st.expander("Technical Details", expanded=False):
                    st.code("\n".join(stats.errors), language="text")

            if valid_txns:
                if st.button("Run Risk Analysis"):
                    with st.spinner("Processing records through risk intelligence engine..."):
                        batch_results = [evaluate_single_transaction(t, merchant_id) for t in valid_txns]
                        st.session_state["batch_results"] = batch_results
                    st.success(f"Analysis complete for {len(batch_results)} records.")

    # Render Results if Batch Results Exist
    if st.session_state["batch_results"]:
        results = st.session_state["batch_results"]

        st.markdown("---")
        render_pipeline_tracker()

        st.markdown("### Risk Overview")
        low_cnt = sum(1 for r in results if r["risk_level"] == "LOW")
        med_cnt = sum(1 for r in results if r["risk_level"] == "MEDIUM")
        high_cnt = sum(1 for r in results if r["risk_level"] == "HIGH" or r["risk_level"] == "CRITICAL")
        review_cnt = sum(1 for r in results if r["decision"] == "MANUAL_REVIEW")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Transactions", len(results))
        m2.metric("Low Risk", low_cnt)
        m3.metric("Medium Risk", med_cnt)
        m4.metric("High Risk", high_cnt)
        m5.metric("Manual Review", review_cnt)

        st.markdown("### Transaction Analysis Table")
        
        table_data = [
            {
                "Transaction ID": r["transaction_id"],
                "Customer": r["customer_id"],
                "Amount": f"${r['amount']:.2f}",
                "Risk": r["risk_level"],
                "Confidence": f"{r['detector_confidence'] * 100:.1f}%",
                "Verifier Score": f"{r['verifier_risk_score']:.3f}",
                "Decision": r["decision"],
                "Action": r["response_action_code"],
            }
            for r in results
        ]
        st.dataframe(table_data, use_container_width=True, hide_index=True)

        st.markdown("#### Select Transaction for Inspection")
        txn_map = {f"{r['transaction_id']} (Customer: {r['customer_id']})": r for r in results}
        selected_txn_key = st.selectbox("Inspect Detail:", list(txn_map.keys()))
        if selected_txn_key:
            render_transaction_detail(txn_map[selected_txn_key])

elif nav_choice == "Integrations":
    st.subheader("Razorpay")
    st.caption("Mock Two-Way Integration")

    col1, col2 = st.columns(2)
    rzp_key_id = col1.text_input("Key ID", value=st.session_state.get("rzp_key_id", "rzp_test_mock"))
    rzp_key_secret = col2.text_input("Key Secret", type="password", value=st.session_state.get("rzp_key_secret", "mock_secret"))

    if st.button("Test Connection"):
        if not rzp_key_id or not rzp_key_secret:
            st.error("Please provide both Key ID and Key Secret.")
        else:
            try:
                from risk_manager.integrations import registry
                provider_inst = registry.get_provider("razorpay")
                conn = provider_inst.authenticate(
                    merchant_id="merchant_razorpay",
                    credentials={"key_id": rzp_key_id, "key_secret": rzp_key_secret}
                )
                registry.add_connection(conn)
                st.session_state["rzp_connected"] = True
                st.session_state["rzp_connection_id"] = conn.connection_id
                st.session_state["rzp_key_id"] = rzp_key_id
                st.session_state["rzp_key_secret"] = rzp_key_secret
                st.session_state["rzp_conn_obj"] = conn
                st.success("✓ Connected")
            except Exception as exc:
                st.session_state["rzp_connected"] = False
                st.error(f"Connection Failed: {str(exc)}")

    if st.session_state.get("rzp_connected"):
        fetched_cnt = len(st.session_state.get("rzp_fetched_txns", []))
        analyzed_cnt = len(st.session_state.get("batch_results", []))
        sent_cnt = st.session_state.get("rzp_results_sent", 0)
        outbound_status = "✓ Delivered to mock provider" if sent_cnt > 0 else "Pending outbound dispatch"

        st.markdown(f"""
        <div style="background-color:#F1F5F9; padding:14px; border-radius:6px; margin: 12px 0; border: 1px solid #E2E8F0;">
            <p style="margin:0 0 6px 0; font-weight:700; color:#0F172A; font-size:15px;">MOCK RAZORPAY ACTIVITY STATUS</p>
            <p style="margin:2px 0; font-size:14px; color:#166534;"><strong>Connection:</strong> Connected</p>
            <p style="margin:2px 0; font-size:14px; color:#0F172A;"><strong>Environment:</strong> MOCK / DEMO</p>
            <p style="margin:2px 0; font-size:14px; color:#0F172A;"><strong>Transactions fetched:</strong> {fetched_cnt}</p>
            <p style="margin:2px 0; font-size:14px; color:#0F172A;"><strong>Transactions analyzed:</strong> {analyzed_cnt}</p>
            <p style="margin:2px 0; font-size:14px; color:#0F172A;"><strong>Risk results sent:</strong> {sent_cnt}</p>
            <p style="margin:2px 0; font-size:14px; color:#0F172A;"><strong>Outbound status:</strong> {outbound_status}</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Fetch Transactions"):
            try:
                from risk_manager.integrations import registry
                provider_inst = registry.get_provider("razorpay")
                conn = registry.get_connection(st.session_state["rzp_connection_id"])
                valid_txns, stats = provider_inst.sync_transactions(conn)
                st.session_state["rzp_fetched_txns"] = valid_txns
                st.session_state["rzp_stats"] = stats
                st.session_state["batch_results"] = []
                st.session_state["rzp_results_sent"] = 0
                st.session_state["rzp_outbound_ack"] = None
                st.rerun()
            except Exception as exc:
                st.error(f"Fetch failed: {str(exc)}")

        if "rzp_stats" in st.session_state:
            stats = st.session_state["rzp_stats"]
            st.markdown(f"**{stats.total_records} transactions fetched**")
            st.markdown(f"- **{stats.valid_records} valid**")
            st.markdown(f"- **{stats.invalid_records} invalid**")
            st.markdown(f"- **0 duplicates**")

        if "rzp_fetched_txns" in st.session_state and st.session_state["rzp_fetched_txns"]:
            if st.button("Run Risk Analysis"):
                with st.spinner("Analyzing Razorpay transactions through M1–M9 Risk Pipeline..."):
                    txns = st.session_state["rzp_fetched_txns"]
                    results = [evaluate_single_transaction(t, "merchant_razorpay") for t in txns]
                    st.session_state["batch_results"] = results
                st.success(f"Analysis complete for {len(results)} Razorpay transactions.")
                st.rerun()

            if st.session_state.get("batch_results"):
                st.markdown("---")
                render_pipeline_tracker()
                st.markdown("### Risk Analysis Results")
                results = st.session_state["batch_results"]

                low_cnt = sum(1 for r in results if r["risk_level"] == "LOW")
                med_cnt = sum(1 for r in results if r["risk_level"] == "MEDIUM")
                high_cnt = sum(1 for r in results if r["risk_level"] in ("HIGH", "CRITICAL"))
                review_cnt = sum(1 for r in results if r["decision"] == "MANUAL_REVIEW")

                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total Transactions", len(results))
                m2.metric("Low Risk", low_cnt)
                m3.metric("Medium Risk", med_cnt)
                m4.metric("High Risk", high_cnt)
                m5.metric("Manual Review", review_cnt)

                table_data = [
                    {
                        "Transaction ID": r["transaction_id"],
                        "Customer": r["customer_id"],
                        "Amount": f"${r['amount']:.2f}",
                        "Risk": r["risk_level"],
                        "Confidence": f"{r['detector_confidence'] * 100:.1f}%",
                        "Verifier Score": f"{r['verifier_risk_score']:.3f}",
                        "Decision": r["decision"],
                        "Action": r["response_action_code"],
                    }
                    for r in results
                ]
                st.dataframe(table_data, use_container_width=True, hide_index=True)

                st.markdown("### Outbound Risk Result Sync")
                st.caption("Send calculated M1–M9 risk assessments back to Razorpay merchant platform.")

                if st.button("Send Results to Mock Razorpay"):
                    try:
                        from risk_manager.integrations import registry
                        provider_inst = registry.get_provider("razorpay")
                        conn = registry.get_connection(st.session_state["rzp_connection_id"])
                        ack_batch = provider_inst.send_batch_risk_results(conn, results)
                        st.session_state["rzp_outbound_ack"] = ack_batch
                        st.session_state["rzp_results_sent"] = ack_batch.get("total_sent", len(results))
                        st.success(f"✓ {ack_batch.get('total_acknowledged')} risk results successfully delivered to Mock Razorpay!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Outbound dispatch failed: {str(exc)}")

                if st.session_state.get("rzp_outbound_ack"):
                    ack = st.session_state["rzp_outbound_ack"]
                    st.info(f"**Provider Acknowledgement Summary:**\n- **Status:** {'SUCCESS' if ack.get('success') else 'FAILED'}\n- **Total Sent:** {ack.get('total_sent')}\n- **Total Acknowledged:** {ack.get('total_acknowledged')}\n- **Provider Mode:** {ack.get('mode')}\n- **Message:** {ack.get('message')}")

                st.markdown("#### Select Transaction for Inspection")
                txn_map = {f"{r['transaction_id']} (Customer: {r['customer_id']})": r for r in results}
                selected_txn_key = st.selectbox("Inspect Razorpay Detail:", list(txn_map.keys()))
                if selected_txn_key:
                    render_transaction_detail(txn_map[selected_txn_key])

elif nav_choice == "Transactions":
    st.subheader("Transaction Workstation")
    st.caption("Search, filter, and review analyzed transaction records.")

    results = st.session_state.get("batch_results", [])
    if not results:
        st.info("No analyzed transactions in current session. Upload data in 'Risk Analysis' or run 'Demo / Test Data'.")
    else:
        # Filters
        c_search, c_risk, c_dec = st.columns([2, 1, 1])
        search_q = c_search.text_input("Search Customer / Txn ID:", "")
        risk_filter = c_risk.selectbox("Risk Level:", ["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
        dec_filter = c_dec.selectbox("Decision:", ["ALL", "APPROVE", "MANUAL_REVIEW", "DEFENSIVE_ACTION"])

        filtered = results
        if search_q.strip():
            q = search_q.strip().lower()
            filtered = [r for r in filtered if q in r["transaction_id"].lower() or q in r["customer_id"].lower()]
        if risk_filter != "ALL":
            filtered = [r for r in filtered if r["risk_level"] == risk_filter]
        if dec_filter != "ALL":
            filtered = [r for r in filtered if r["decision"] == dec_filter]

        st.write(f"Showing **{len(filtered)}** of **{len(results)}** records")

        table_data = [
            {
                "Transaction ID": r["transaction_id"],
                "Customer": r["customer_id"],
                "Amount": f"${r['amount']:.2f}",
                "Risk": r["risk_level"],
                "Confidence": f"{r['detector_confidence'] * 100:.1f}%",
                "Verifier Score": f"{r['verifier_risk_score']:.3f}",
                "Decision": r["decision"],
                "Action": r["response_action_code"],
            }
            for r in filtered
        ]
        st.dataframe(table_data, use_container_width=True, hide_index=True)

        if filtered:
            txn_map = {f"{r['transaction_id']} (Customer: {r['customer_id']})": r for r in filtered}
            selected_txn_key = st.selectbox("Inspect Transaction Detail:", list(txn_map.keys()))
            if selected_txn_key:
                render_transaction_detail(txn_map[selected_txn_key])

elif nav_choice == "Audit Trail":
    st.subheader("Audit & Compliance Trail")
    st.caption("Immutable record of risk assessments, model versions, and executed defensive actions.")

    results = st.session_state.get("batch_results", [])
    if not results:
        st.info("No audit records available in current session.")
    else:
        audit_rows = [
            {
                "Audit ID": r["audit_id"],
                "Transaction ID": r["transaction_id"],
                "Merchant": r["merchant_id"].upper(),
                "Decision": r["decision"],
                "Action Type": r["response_action_type"],
                "Execution Status": r["mock_execution_status"],
                "Model Version": "detector-rf-1.0",
                "Timestamp": r["timestamp"],
            }
            for r in results
        ]
        st.dataframe(audit_rows, use_container_width=True, hide_index=True)

elif nav_choice == "Demo / Test Data":
    st.markdown('<span class="demo-badge">DEMO DATA</span>', unsafe_allow_html=True)
    st.subheader("Synthetic Test Scenarios & Datasets")
    st.caption("Pre-configured scenarios for testing defensive pipeline capabilities.")

    demo_mode = st.radio("Select Demo Source:", ["Pre-built Test Scenarios", "Synthetic Dataset Files"])

    if demo_mode == "Pre-built Test Scenarios":
        demo_results = get_demo_results()
        scenario_map = {
            f"Scenario {r['scenario_idx']}: {r['scenario_name'].replace('_', ' ').title()} ({r['transaction_id']})": r
            for r in demo_results
        }
        sel_key = st.selectbox("Select Test Scenario:", list(scenario_map.keys()))
        if sel_key:
            scen_data = scenario_map[sel_key]
            # Convert demo output to standard evaluated transaction format
            res_eval = {
                "transaction_id": scen_data["transaction_id"],
                "order_id": scen_data.get("order_id", scen_data["transaction_id"]),
                "customer_id": scen_data.get("customer_id", "C-DEMO-100"),
                "merchant_id": scen_data.get("merchant_id", "merchant_a"),
                "currency": "USD",
                "payment_method": "CARD",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "transaction_status": "COMPLETED",
                "scenario_name": scen_data["scenario_name"],
                "case_type": scen_data["case_type"],
                "amount": float(scen_data["amount"]),
                "detector_confidence": scen_data["detector_confidence"],
                "verifier_status": scen_data["verifier_status"],
                "verifier_risk_score": scen_data["verifier_risk_score"],
                "risk_level": "HIGH" if scen_data["verifier_risk_score"] > 0.5 else "LOW",
                "shap_top_features": scen_data.get("shap_top_features", []),
                "decision": scen_data["decision"],
                "expected_loss_by_action": scen_data["expected_loss_by_action"],
                "human_explanation": f"Evaluation for synthetic demo scenario {scen_data['scenario_name']}.",
                "response_action_code": scen_data["response_action_code"],
                "response_action_type": scen_data["response_action_type"],
                "response_message": scen_data["response_message"],
                "mock_execution_status": scen_data["mock_execution_status"],
                "mock_executed_steps": scen_data["mock_executed_steps"],
                "audit_id": scen_data["audit_id"],
            }
            render_pipeline_tracker()
            render_transaction_detail(res_eval)

    else:
        sample_choice = st.selectbox(
            "Select Synthetic Dataset File:",
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
            st.write(f"Dataset Loaded: `{file_path}` ({stats.total_records} records)")
            if st.button("Load and Run Analysis on Synthetic Dataset"):
                with st.spinner("Processing synthetic records..."):
                    batch_results = [evaluate_single_transaction(t, merchant_id) for t in valid_txns]
                    st.session_state["batch_results"] = batch_results
                st.success(f"Analysis complete for {len(batch_results)} records. View in 'Risk Analysis' or 'Transactions' tab.")
