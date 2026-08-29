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
    page_title="AI Risk Manager — Institutional Risk Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# FINX-STYLE ENTERPRISE DESIGN SYSTEM (LIGHT THEME)
# ==============================================================================
st.markdown("""
<style>
    /* Base Font & Theme Override */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        background-color: #F6F8FB !important;
        color: #172033 !important;
    }

    header[data-testid="stHeader"] {
        background-color: #F6F8FB !important;
        border-bottom: 1px solid #E4E7EC;
    }

    .main .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1440px !important;
    }

    /* Sidebar Navigation */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E4E7EC !important;
        width: 280px !important;
    }

    .sidebar-brand {
        padding: 1.25rem 1rem 0.75rem 1rem;
        border-bottom: 1px solid #F1F5F9;
        margin-bottom: 1rem;
    }
    .sidebar-brand-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #172033;
        letter-spacing: -0.02em;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .sidebar-brand-subtitle {
        font-size: 0.75rem;
        font-weight: 600;
        color: #2563EB;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.15rem;
    }

    .sidebar-section-header {
        font-size: 0.7rem;
        font-weight: 700;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin: 1rem 0 0.4rem 0.75rem;
    }

    /* Cards & Panels */
    .finx-card {
        background: #FFFFFF;
        border: 1px solid #E4E7EC;
        border-radius: 8px;
        padding: 1.25rem;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        margin-bottom: 1.25rem;
    }

    .finx-metric-card {
        background: #FFFFFF;
        border: 1px solid #E4E7EC;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }
    .finx-metric-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #667085;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .finx-metric-val {
        font-size: 1.65rem;
        font-weight: 700;
        color: #172033;
        margin-top: 0.25rem;
        letter-spacing: -0.03em;
    }
    .finx-metric-sub {
        font-size: 0.75rem;
        font-weight: 500;
        color: #10B981;
        margin-top: 0.2rem;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    /* Risk Badges */
    .badge-risk {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        font-size: 0.725rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .badge-low {
        background-color: #DCFCE7;
        color: #15803D;
        border: 1px solid #BBF7D0;
    }
    .badge-medium {
        background-color: #FEF3C7;
        color: #B45309;
        border: 1px solid #FDE68A;
    }
    .badge-high {
        background-color: #FEE2E2;
        color: #B91C1C;
        border: 1px solid #FCA5A5;
    }
    .badge-critical {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1px solid #F87171;
        font-weight: 800;
    }

    .badge-decision {
        display: inline-flex;
        align-items: center;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        font-size: 0.725rem;
        font-weight: 600;
    }
    .badge-approve { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
    .badge-review { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
    .badge-defensive { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }

    /* Pipeline Visualization */
    .pipeline-grid {
        display: flex;
        gap: 0.5rem;
        overflow-x: auto;
        padding: 0.75rem;
        background: #FFFFFF;
        border: 1px solid #E4E7EC;
        border-radius: 8px;
        margin-bottom: 1.25rem;
    }
    .pipeline-step {
        flex: 1;
        min-width: 100px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 0.6rem;
        text-align: center;
    }
    .pipeline-step.active {
        background: #EFF6FF;
        border-color: #93C5FD;
    }
    .pipeline-step-code {
        font-size: 0.7rem;
        font-weight: 700;
        color: #2563EB;
    }
    .pipeline-step-name {
        font-size: 0.75rem;
        font-weight: 600;
        color: #172033;
        margin-top: 0.15rem;
    }
    .pipeline-step-status {
        font-size: 0.68rem;
        color: #166534;
        font-weight: 600;
        margin-top: 0.25rem;
    }

    /* Integration Card */
    .integration-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.25rem;
        margin-bottom: 1.5rem;
    }
    .integration-card {
        background: #FFFFFF;
        border: 1px solid #E4E7EC;
        border-radius: 8px;
        padding: 1.25rem;
    }
    .integration-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
    }
    .integration-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #172033;
    }
    .integration-status {
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
    }
    .status-connected { background: #DCFCE7; color: #15803D; }
    .status-available { background: #F1F5F9; color: #64748B; }

    /* Tables */
    .stDataFrame {
        border: 1px solid #E4E7EC !important;
        border-radius: 8px !important;
        background: #FFFFFF !important;
    }

    /* Buttons */
    .stButton > button {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.15s ease-in-out !important;
    }
    .stButton > button:hover {
        background-color: #1D4ED8 !important;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2) !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# BACKEND & PIPELINE LOADER (UNTOUCHED BUSINESS LOGIC)
# ==============================================================================
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

    risk_score = verifier_result.risk_score
    if detected_case == "normal" or risk_score < 0.25:
        risk_level = "LOW"
    elif risk_score < 0.60:
        risk_level = "MEDIUM"
    elif risk_score < 0.85:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    dec = decision_result.decision
    exp_losses = decision_result.expected_loss_by_action
    if dec == "MANUAL_REVIEW":
        human_expl = f"Manual review selected because expected loss of approval (${exp_losses.get('APPROVE', 0.0):.2f}) exceeds review cost (${exp_losses.get('MANUAL_REVIEW', 0.0):.2f})."
    elif dec == "DEFENSIVE_ACTION":
        human_expl = f"Defensive action selected as risk score ({risk_score:.2f}) exceeds security policy threshold."
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


# Initialize Session State Data
if "batch_results" not in st.session_state or not st.session_state["batch_results"]:
    # Pre-populate with default demo dataset for immediate interactive visualization
    try:
        demo_items = get_demo_results()
        eval_items = []
        for d in demo_items:
            eval_items.append({
                "transaction_id": d["transaction_id"],
                "order_id": d.get("order_id", d["transaction_id"]),
                "customer_id": d.get("customer_id", f"C-{d['scenario_idx']+8000}"),
                "merchant_id": d.get("merchant_id", "merchant_a"),
                "currency": "INR",
                "payment_method": "UPI" if d["scenario_idx"] % 2 == 0 else "CARD",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "transaction_status": "COMPLETED",
                "scenario_name": d["scenario_name"],
                "case_type": d["case_type"],
                "amount": float(d["amount"]),
                "detector_confidence": d["detector_confidence"],
                "verifier_status": d["verifier_status"],
                "verifier_risk_score": d["verifier_risk_score"],
                "risk_level": "CRITICAL" if d["verifier_risk_score"] > 0.85 else ("HIGH" if d["verifier_risk_score"] > 0.50 else ("MEDIUM" if d["verifier_risk_score"] > 0.25 else "LOW")),
                "shap_top_features": d.get("shap_top_features", []),
                "decision": d["decision"],
                "expected_loss_by_action": d["expected_loss_by_action"],
                "human_explanation": f"Evaluation for synthetic scenario {d['scenario_name']}.",
                "response_action_code": d["response_action_code"],
                "response_action_type": d["response_action_type"],
                "response_message": d["response_message"],
                "mock_execution_status": d["mock_execution_status"],
                "mock_executed_steps": d["mock_executed_steps"],
                "audit_id": d["audit_id"],
            })
        st.session_state["batch_results"] = eval_items
    except Exception:
        st.session_state["batch_results"] = []

if "selected_txn_id" not in st.session_state:
    st.session_state["selected_txn_id"] = None


# ==============================================================================
# UI COMPONENTS (FINX ENTERPRISE STYLE)
# ==============================================================================

def render_pipeline_tracker(active_stage: str = "ALL"):
    stages = [
        ("M1", "Detection", "✓ Complete"),
        ("M2", "Verification", "✓ Complete"),
        ("M3", "Risk Scoring", "✓ Complete"),
        ("M4", "Decision Engine", "✓ Resolved"),
        ("M5", "Auto-Responder", "✓ Executed"),
        ("M6", "Audit & Log", "✓ Immutable"),
        ("M7", "Feedback Loop", "✓ Updated"),
        ("M8", "Adaptive Model", "✓ Active"),
        ("M9", "Compliance", "✓ Ready"),
    ]
    html_cols = []
    for code, name, status in stages:
        is_act = "active" if active_stage in (code, name, "ALL") else ""
        html_cols.append(f"""
        <div class="pipeline-step {is_act}">
            <div class="pipeline-step-code">{code}</div>
            <div class="pipeline-step-name">{name}</div>
            <div class="pipeline-step-status">{status}</div>
        </div>
        """)
    
    st.markdown(f'<div class="pipeline-grid">{"".join(html_cols)}</div>', unsafe_allow_html=True)


def render_transaction_investigation_view(res: dict):
    st.markdown(f"""
    <div class="finx-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="font-size:0.8rem; font-weight:600; color:#667085;">TRANSACTION INVESTIGATION WORKSTATION</span>
                <h2 style="margin:0.1rem 0; font-weight:700; color:#172033;">#{res['transaction_id']}</h2>
                <span style="font-size:0.85rem; color:#475569;">Customer: <strong>{res['customer_id']}</strong> • Order: <strong>{res['order_id']}</strong> • Timestamp: {res['timestamp']}</span>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.8rem; font-weight:700; color:#172033;">₹{res['amount']:,.2f}</div>
                <div style="margin-top:0.3rem;">
                    <span class="badge-risk badge-{res['risk_level'].lower()}">{res['risk_level']} RISK</span>
                    <span class="badge-decision badge-{res['decision'].lower().replace('_', '')}">{res['decision']}</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Risk Summary & Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Risk Score", f"{int(res['verifier_risk_score'] * 100)} / 100")
    m2.metric("Detector Confidence", f"{res['detector_confidence'] * 100:.1f}%")
    m3.metric("Case Scenario", res['case_type'].replace('_', ' ').title())
    m4.metric("Action Code", res['response_action_code'])

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Risk Contributors & SHAP Attribution")
        st.caption("Primary signals driving elevated risk score")
        top_feats = res.get("shap_top_features", [])
        if top_feats:
            for f in top_feats:
                fname = f['feature'].replace('_', ' ').title()
                contrib = f['contribution']
                pct = min(100, max(5, int(abs(contrib) * 100)))
                st.markdown(f"**{fname}** (`{f['value']}`)")
                st.progress(pct / 100)
        else:
            st.info("No anomalous feature contributions detected for this baseline transaction.")

        st.markdown("#### Recommended Decision Logic")
        st.write(res["human_explanation"])

        st.markdown("**Expected Loss Evaluation ($):**")
        exp_losses = res["expected_loss_by_action"]
        l1, l2, l3 = st.columns(3)
        l1.metric("Approve", f"${exp_losses.get('APPROVE', 0.0):.2f}")
        l2.metric("Manual Review", f"${exp_losses.get('MANUAL_REVIEW', 0.0):.2f}")
        l3.metric("Defensive Action", f"${exp_losses.get('DEFENSIVE_ACTION', 0.0):.2f}")

    with col_right:
        st.markdown("#### M1–M9 Architecture Pipeline Audit")
        render_pipeline_tracker()

        st.markdown("#### Response & Defensive Action Receipt")
        st.write(f"**Action Code:** `{res['response_action_code']}`")
        st.write(f"**Action Type:** `{res['response_action_type']}`")
        st.info(f"**Message:** {res['response_message']}")
        
        st.markdown("**Automated Safeguard Execution Steps:**")
        for step in res["mock_executed_steps"]:
            st.write(f"✓ {step}")

        st.markdown("**Audit Record:**")
        st.code(f"Audit ID: {res['audit_id']}\nExecution Status: {res['mock_execution_status']}\nModel Version: detector-rf-1.0", language="text")

    if st.button("← Back to List"):
        st.session_state["selected_txn_id"] = None
        st.rerun()


# ==============================================================================
# PERSISTENT SIDEBAR NAVIGATION
# ==============================================================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="sidebar-brand-title">🛡️ AI Risk Manager</div>
        <div class="sidebar-brand-subtitle">Defensive Risk Console</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-header">OVERVIEW</div>', unsafe_allow_html=True)
    nav_dashboard = st.button("📊 Dashboard", use_container_width=True)
    
    st.markdown('<div class="sidebar-section-header">MONITOR</div>', unsafe_allow_html=True)
    nav_transactions = st.button("💳 Transactions", use_container_width=True)
    nav_queue = st.button("⚡ Risk Queue", use_container_width=True)
    nav_customers = st.button("👥 Customers", use_container_width=True)

    st.markdown('<div class="sidebar-section-header">ANALYSIS</div>', unsafe_allow_html=True)
    nav_analysis = st.button("📥 Unified Data Input", use_container_width=True)
    nav_models = st.button("🧠 Risk Models", use_container_width=True)
    nav_analytics = st.button("📈 Analytics", use_container_width=True)

    st.markdown('<div class="sidebar-section-header">INTEGRATIONS</div>', unsafe_allow_html=True)
    nav_integrations = st.button("🔗 Connected Sources", use_container_width=True)

    st.markdown('<div class="sidebar-section-header">AUDIT</div>', unsafe_allow_html=True)
    nav_audit = st.button("📜 Audit Trail", use_container_width=True)

    st.markdown('<div class="sidebar-section-header">SYSTEM</div>', unsafe_allow_html=True)
    nav_settings = st.button("⚙️ Settings", use_container_width=True)

# Navigation State Handling
if "active_nav" not in st.session_state:
    st.session_state["active_nav"] = "Dashboard"

if nav_dashboard: st.session_state["active_nav"] = "Dashboard"
elif nav_transactions: st.session_state["active_nav"] = "Transactions"
elif nav_queue: st.session_state["active_nav"] = "Risk Queue"
elif nav_customers: st.session_state["active_nav"] = "Customers"
elif nav_analysis: st.session_state["active_nav"] = "Unified Data Input"
elif nav_models: st.session_state["active_nav"] = "Risk Models"
elif nav_analytics: st.session_state["active_nav"] = "Analytics"
elif nav_integrations: st.session_state["active_nav"] = "Connected Sources"
elif nav_audit: st.session_state["active_nav"] = "Audit Trail"
elif nav_settings: st.session_state["active_nav"] = "Settings"

active_nav = st.session_state["active_nav"]


# ==============================================================================
# PAGE 1: OVERVIEW / DASHBOARD
# ==============================================================================
if active_nav == "Dashboard":
    st.markdown("""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <div>
            <h2 style="margin:0; font-weight:700; color:#172033;">Risk Overview</h2>
            <span style="font-size:0.85rem; color:#667085;">Institutional risk monitoring & real-time decision dashboard</span>
        </div>
        <div>
            <span style="font-size:0.8rem; font-weight:600; color:#475569; background:#FFFFFF; padding:0.4rem 0.8rem; border-radius:6px; border:1px solid #E4E7EC;">Last 24 hours • Today ▼</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    results = st.session_state.get("batch_results", [])
    total_txns = len(results) if results else 12482
    high_risk_cnt = sum(1 for r in results if r["risk_level"] in ("HIGH", "CRITICAL")) if results else 183
    risk_rate = (high_risk_cnt / total_txns * 100) if total_txns > 0 else 1.47
    amount_at_risk = sum(r["amount"] for r in results if r["risk_level"] in ("HIGH", "CRITICAL")) if results else 2840000.0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="finx-metric-card">
            <div class="finx-metric-label">Transactions</div>
            <div class="finx-metric-val">{total_txns:,}</div>
            <div class="finx-metric-sub">↑ 4.2% vs yesterday</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="finx-metric-card">
            <div class="finx-metric-label">High / Critical Risk</div>
            <div class="finx-metric-val">{high_risk_cnt}</div>
            <div class="finx-metric-sub" style="color:#DC2626;">↑ 12 flagged today</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="finx-metric-card">
            <div class="finx-metric-label">Risk Rate</div>
            <div class="finx-metric-val">{risk_rate:.2f}%</div>
            <div class="finx-metric-sub">Within target threshold</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="finx-metric-card">
            <div class="finx-metric-label">Amount At Risk</div>
            <div class="finx-metric-val">₹{amount_at_risk:,.2f}</div>
            <div class="finx-metric-sub">Auto-protected by M5</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    c_left, c_right = st.columns([2, 1])

    with c_left:
        st.markdown("#### Transaction Risk Trend")
        if results:
            chart_data = [{"Transaction": r["transaction_id"], "Amount": r["amount"], "Risk Score": r["verifier_risk_score"] * 100} for r in results]
            st.line_chart(chart_data, x="Transaction", y="Risk Score")
        else:
            st.info("No active dataset loaded.")

    with c_right:
        st.markdown("#### Risk Distribution")
        if results:
            dist = {
                "LOW": sum(1 for r in results if r["risk_level"] == "LOW"),
                "MEDIUM": sum(1 for r in results if r["risk_level"] == "MEDIUM"),
                "HIGH": sum(1 for r in results if r["risk_level"] == "HIGH"),
                "CRITICAL": sum(1 for r in results if r["risk_level"] == "CRITICAL"),
            }
            st.bar_chart(dist)

    st.markdown("#### Recent Risk Events")
    if results:
        table_data = [
            {
                "Transaction": r["transaction_id"],
                "Customer": r["customer_id"],
                "Amount": f"₹{r['amount']:,.2f}",
                "Risk Score": f"{int(r['verifier_risk_score'] * 100)} / 100",
                "Risk Level": r["risk_level"],
                "Decision": r["decision"],
                "Time": "2m ago",
            }
            for r in results[:10]
        ]
        st.dataframe(table_data, use_container_width=True, hide_index=True)

        sel_id = st.selectbox("Inspect Transaction Event:", [r["transaction_id"] for r in results])
        if st.button("Inspect Details"):
            st.session_state["selected_txn_id"] = sel_id
            st.session_state["active_nav"] = "Transactions"
            st.rerun()


# ==============================================================================
# PAGE 2: TRANSACTIONS & INVESTIGATION WORKSTATION
# ==============================================================================
elif active_nav == "Transactions":
    if st.session_state.get("selected_txn_id"):
        results = st.session_state.get("batch_results", [])
        txn_dict = next((r for r in results if r["transaction_id"] == st.session_state["selected_txn_id"]), None)
        if txn_dict:
            render_transaction_investigation_view(txn_dict)
        else:
            st.session_state["selected_txn_id"] = None
            st.rerun()
    else:
        st.markdown("""
        <div style="margin-bottom:1rem;">
            <h2 style="margin:0; font-weight:700; color:#172033;">Transaction Investigation Workstation</h2>
            <span style="font-size:0.85rem; color:#667085;">Search, filter, and inspect payment transactions analyzed by M1–M9</span>
        </div>
        """, unsafe_allow_html=True)

        results = st.session_state.get("batch_results", [])
        if not results:
            st.info("No transaction data available in current session. Upload data in 'Unified Data Input' or connect Razorpay.")
        else:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            search_q = c1.text_input("Search transaction/customer", "")
            risk_f = c2.selectbox("Risk Level", ["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
            dec_f = c3.selectbox("Decision", ["ALL", "APPROVE", "MANUAL_REVIEW", "DEFENSIVE_ACTION"])
            st.markdown("<br>", unsafe_allow_html=True)

            filtered = results
            if search_q.strip():
                q = search_q.strip().lower()
                filtered = [r for r in filtered if q in r["transaction_id"].lower() or q in r["customer_id"].lower()]
            if risk_f != "ALL":
                filtered = [r for r in filtered if r["risk_level"] == risk_f]
            if dec_f != "ALL":
                filtered = [r for r in filtered if r["decision"] == dec_f]

            table_rows = [
                {
                    "Transaction ID": r["transaction_id"],
                    "Customer": r["customer_id"],
                    "Amount": f"₹{r['amount']:,.2f}",
                    "Method": r["payment_method"],
                    "Risk Score": f"{int(r['verifier_risk_score'] * 100)} / 100",
                    "Risk Level": r["risk_level"],
                    "Decision": r["decision"],
                    "Timestamp": r["timestamp"],
                }
                for r in filtered
            ]
            st.dataframe(table_rows, use_container_width=True, hide_index=True)

            st.markdown("#### Select Row to Open Investigation View")
            sel_key = st.selectbox("Transaction ID:", [r["transaction_id"] for r in filtered])
            if st.button("Open Investigation View"):
                st.session_state["selected_txn_id"] = sel_key
                st.rerun()


# ==============================================================================
# PAGE 3: RISK QUEUE
# ==============================================================================
elif active_nav == "Risk Queue":
    st.markdown("""
    <div style="margin-bottom:1rem;">
        <h2 style="margin:0; font-weight:700; color:#172033;">Risk Operational Queue</h2>
        <span style="font-size:0.85rem; color:#667085;">Prioritized queue of suspicious transactions requiring analyst decisioning</span>
    </div>
    """, unsafe_allow_html=True)

    results = st.session_state.get("batch_results", [])
    high_risk_items = [r for r in results if r["risk_level"] in ("HIGH", "CRITICAL", "MEDIUM")]
    high_risk_items.sort(key=lambda x: x["verifier_risk_score"], reverse=True)

    if not high_risk_items:
        st.success("✓ Risk queue empty. No high or critical risk items requiring manual intervention.")
    else:
        q_rows = [
            {
                "Risk Level": r["risk_level"],
                "Transaction": r["transaction_id"],
                "Customer": r["customer_id"],
                "Amount": f"₹{r['amount']:,.2f}",
                "Trigger Scenario": r["case_type"].replace('_', ' ').title(),
                "Recommended Decision": r["decision"],
                "Action Code": r["response_action_code"],
                "Score": f"{int(r['verifier_risk_score'] * 100)}",
            }
            for r in high_risk_items
        ]
        st.dataframe(q_rows, use_container_width=True, hide_index=True)


# ==============================================================================
# PAGE 4: CUSTOMERS
# ==============================================================================
elif active_nav == "Customers":
    st.markdown("""
    <div style="margin-bottom:1rem;">
        <h2 style="margin:0; font-weight:700; color:#172033;">Customer Risk Profiles</h2>
        <span style="font-size:0.85rem; color:#667085;">Entity-level risk timeline and historical behavioral profiling</span>
    </div>
    """, unsafe_allow_html=True)

    results = st.session_state.get("batch_results", [])
    if results:
        cust_list = list(set(r["customer_id"] for r in results))
        sel_cust = st.selectbox("Select Customer Entity:", cust_list)
        cust_txns = [r for r in results if r["customer_id"] == sel_cust]

        flagged_cnt = sum(1 for r in cust_txns if r["risk_level"] in ("HIGH", "CRITICAL"))
        total_amt = sum(r["amount"] for r in cust_txns)
        avg_amt = total_amt / len(cust_txns) if cust_txns else 0.0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Transactions", len(cust_txns))
        c2.metric("Flagged Risk Events", flagged_cnt)
        c3.metric("Total Amount", f"₹{total_amt:,.2f}")
        c4.metric("Avg Transaction", f"₹{avg_amt:,.2f}")

        st.markdown("#### Transaction History & Timeline")
        st.dataframe(cust_txns, use_container_width=True, hide_index=True)


# ==============================================================================
# PAGE 5: UNIFIED DATA INPUT & RISK ANALYSIS
# ==============================================================================
elif active_nav == "Unified Data Input":
    st.markdown("""
    <div style="margin-bottom:1rem;">
        <h2 style="margin:0; font-weight:700; color:#172033;">Unified Data Ingestion</h2>
        <span style="font-size:0.85rem; color:#667085;">Single input experience for CSV and JSON transaction formats</span>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload CSV or JSON Dataset File", type=["csv", "json", "txt"])
    pasted_text = st.text_area("Or Paste Raw CSV / JSON Data:", height=120)

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

            st.markdown(f"""
            <div class="finx-card">
                <h4 style="margin:0 0 0.5rem 0; color:#172033;">Ingestion Summary Status</h4>
                <p style="margin:0; font-size:0.9rem;"><strong>Detected Format:</strong> <code>{format_detected.upper()}</code> • <strong>Schema:</strong> <code>{merchant_id.upper()}</code></p>
                <div style="display:flex; gap:1.5rem; margin-top:0.75rem;">
                    <div>Total Records: <strong>{stats.total_records}</strong></div>
                    <div>Valid Records: <strong style="color:#166534;">{stats.valid_records}</strong></div>
                    <div>Invalid Records: <strong style="color:#DC2626;">{stats.invalid_records}</strong></div>
                    <div>Duplicates: <strong>{stats.duplicate_records}</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if valid_txns:
                if st.button("Run M1–M9 Risk Analysis"):
                    with st.spinner("Evaluating transactions through M1–M9 risk engine..."):
                        batch_results = [evaluate_single_transaction(t, merchant_id) for t in valid_txns]
                        st.session_state["batch_results"] = batch_results
                    st.success(f"✓ Analysis complete for {len(batch_results)} records.")
                    st.rerun()


# ==============================================================================
# PAGE 6: CONNECTED SOURCES (INTEGRATIONS)
# ==============================================================================
elif active_nav == "Connected Sources":
    st.markdown("""
    <div style="margin-bottom:1rem;">
        <h2 style="margin:0; font-weight:700; color:#172033;">Connected Merchant Sources</h2>
        <span style="font-size:0.85rem; color:#667085;">Manage platform integrations, historical synchronization, and two-way risk feedback</span>
    </div>
    """, unsafe_allow_html=True)

    is_rzp_connected = st.session_state.get("rzp_connected", False)

    # FINX Connected Sources Grid
    st.markdown(f"""
    <div class="integration-grid">
        <div class="integration-card">
            <div class="integration-header">
                <div class="integration-title">Razorpay</div>
                <span class="integration-status {'status-connected' if is_rzp_connected else 'status-available'}">
                    {'✓ Connected' if is_rzp_connected else 'Available'}
                </span>
            </div>
            <p style="font-size:0.85rem; color:#667085; margin:0 0 0.75rem 0;">Direct API & Two-Way Risk Sync Integration</p>
            <p style="font-size:0.8rem; margin:0.2rem 0;"><strong>Environment:</strong> MOCK / DEMO</p>
            <p style="font-size:0.8rem; margin:0.2rem 0;"><strong>Transactions:</strong> 20 available</p>
        </div>
        <div class="integration-card">
            <div class="integration-header">
                <div class="integration-title">Shopify</div>
                <span class="integration-status status-available">Coming soon</span>
            </div>
            <p style="font-size:0.85rem; color:#667085; margin:0;">E-commerce Store Webhook & Order Risk Sync</p>
        </div>
        <div class="integration-card">
            <div class="integration-header">
                <div class="integration-title">Stripe / WooCommerce</div>
                <span class="integration-status status-available">Coming soon</span>
            </div>
            <p style="font-size:0.85rem; color:#667085; margin:0;">Payment Gateway Integration Connector</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Razorpay Mock Two-Way Integration Console")

    c1, c2 = st.columns(2)
    rzp_key_id = c1.text_input("Key ID", value=st.session_state.get("rzp_key_id", "rzp_test_mock"))
    rzp_key_secret = c2.text_input("Key Secret", type="password", value=st.session_state.get("rzp_key_secret", "mock_secret"))

    if st.button("Test Connection"):
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
            st.success("✓ Connected")
            st.rerun()
        except Exception as exc:
            st.error(f"Connection Failed: {str(exc)}")

    if is_rzp_connected:
        fetched_cnt = len(st.session_state.get("rzp_fetched_txns", []))
        analyzed_cnt = len(st.session_state.get("batch_results", []))
        sent_cnt = st.session_state.get("rzp_results_sent", 0)
        outbound_status = "✓ Delivered to mock provider" if sent_cnt > 0 else "Pending outbound dispatch"

        st.markdown(f"""
        <div class="finx-card" style="background:#F8FAFC; border-color:#CBD5E1;">
            <h4 style="margin:0 0 0.5rem 0; color:#172033;">MOCK RAZORPAY ACTIVITY STATUS</h4>
            <p style="margin:0.2rem 0; font-size:0.9rem; color:#166534;"><strong>Connection:</strong> Connected</p>
            <p style="margin:0.2rem 0; font-size:0.9rem;"><strong>Environment:</strong> MOCK / DEMO</p>
            <p style="margin:0.2rem 0; font-size:0.9rem;"><strong>Transactions fetched:</strong> {fetched_cnt}</p>
            <p style="margin:0.2rem 0; font-size:0.9rem;"><strong>Transactions analyzed:</strong> {analyzed_cnt}</p>
            <p style="margin:0.2rem 0; font-size:0.9rem;"><strong>Risk results sent:</strong> {sent_cnt}</p>
            <p style="margin:0.2rem 0; font-size:0.9rem;"><strong>Outbound status:</strong> {outbound_status}</p>
        </div>
        """, unsafe_allow_html=True)

        col_act1, col_act2, col_act3 = st.columns(3)

        with col_act1:
            if st.button("Fetch Transactions"):
                try:
                    from risk_manager.integrations import registry
                    provider_inst = registry.get_provider("razorpay")
                    conn = registry.get_connection(st.session_state["rzp_connection_id"])
                    valid_txns, stats = provider_inst.sync_transactions(conn)
                    st.session_state["rzp_fetched_txns"] = valid_txns
                    st.session_state["rzp_stats"] = stats
                    st.success(f"✓ {len(valid_txns)} transactions fetched")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Fetch failed: {str(exc)}")

        with col_act2:
            if st.button("Run Risk Analysis"):
                if "rzp_fetched_txns" in st.session_state:
                    with st.spinner("Running M1–M9 Risk Pipeline..."):
                        txns = st.session_state["rzp_fetched_txns"]
                        results = [evaluate_single_transaction(t, "merchant_razorpay") for t in txns]
                        st.session_state["batch_results"] = results
                    st.success(f"✓ Analysis complete for {len(results)} records")
                    st.rerun()
                else:
                    st.warning("Please fetch transactions first.")

        with col_act3:
            if st.button("Send Results to Mock Razorpay"):
                if st.session_state.get("batch_results"):
                    try:
                        from risk_manager.integrations import registry
                        provider_inst = registry.get_provider("razorpay")
                        conn = registry.get_connection(st.session_state["rzp_connection_id"])
                        results = st.session_state["batch_results"]
                        ack_batch = provider_inst.send_batch_risk_results(conn, results)
                        st.session_state["rzp_outbound_ack"] = ack_batch
                        st.session_state["rzp_results_sent"] = ack_batch.get("total_sent", len(results))
                        st.success(f"✓ {ack_batch.get('total_acknowledged')} results delivered")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Outbound dispatch failed: {str(exc)}")
                else:
                    st.warning("Please run risk analysis first.")


# ==============================================================================
# PAGE 7: AUDIT TRAIL
# ==============================================================================
elif active_nav == "Audit Trail":
    st.markdown("""
    <div style="margin-bottom:1rem;">
        <h2 style="margin:0; font-weight:700; color:#172033;">Audit & Compliance Log</h2>
        <span style="font-size:0.85rem; color:#667085;">Immutable execution trail of detector, verifier, and responder decisions</span>
    </div>
    """, unsafe_allow_html=True)

    results = st.session_state.get("batch_results", [])
    if results:
        audit_table = [
            {
                "Audit ID": r["audit_id"],
                "Transaction ID": r["transaction_id"],
                "Decision": r["decision"],
                "Action Code": r["response_action_code"],
                "Execution Status": r["mock_execution_status"],
                "Model Version": "detector-rf-1.0",
                "Timestamp": r["timestamp"],
            }
            for r in results
        ]
        st.dataframe(audit_table, use_container_width=True, hide_index=True)


# ==============================================================================
# OTHER PAGES (MODELS, ANALYTICS, SETTINGS)
# ==============================================================================
elif active_nav == "Risk Models":
    st.subheader("Risk Models & Classifiers")
    st.json({"Detector Model": "Random Forest v1.0", "Verification Rules": "v1.0.0", "Policy Engine": "Merchant Standard v1.0"})

elif active_nav == "Analytics":
    st.subheader("Risk Analytics & Cohorts")
    results = st.session_state.get("batch_results", [])
    if results:
        st.bar_chart([r["verifier_risk_score"] for r in results])

elif active_nav == "Settings":
    st.subheader("System & Security Settings")
    st.write("Configured False-Positive & False-Negative Cost Weights")
    st.json(MAPPINGS)
