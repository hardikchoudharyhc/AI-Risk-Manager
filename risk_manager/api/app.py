from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from data.synthetic.dataset_generator import create_synthetic_dataset
from risk_manager.decision import DecisionEngine
from risk_manager.detector import generate_labeled_dataset, train_detector, Predictor
from risk_manager.demo import extract_detector_features
from risk_manager.features import FeatureEngine
from risk_manager.models import Transaction
from risk_manager.responder import AutoResponder, MockActionAdapter
from risk_manager.verification import VerificationService
from risk_manager.verification.types import VerificationResult, ModelExplanation

ROOT = Path(__file__).parents[2]


class RiskAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(..., min_length=1, description="Unique transaction ID")
    order_id: str = Field(..., min_length=1, description="Associated order ID")
    customer_id: str = Field(..., min_length=1, description="Associated customer ID")
    amount: Decimal = Field(..., gt=0, description="Transaction amount in monetary units")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency code (e.g. USD)")
    payment_method: str = Field(default="CARD", description="Payment method used")
    transaction_status: str = Field(default="PENDING", description="Status of transaction")
    timestamp: datetime | None = Field(default=None, description="ISO timestamp of transaction")
    merchant_id: str = Field(default="merchant_a", description="Merchant configuration identifier")


class RiskAnalyzeResponse(BaseModel):
    transaction_id: str
    merchant_id: str
    case_type: str
    detector_confidence: float
    verifier_status: str
    verifier_risk_score: float
    evidence_reasons: list[str]
    shap_explanation: list[dict[str, Any]]
    decision: str
    expected_losses: dict[str, float]
    selected_expected_loss: float
    responder_action_code: str
    responder_action_type: str
    defensive_message: str
    mock_execution_status: str
    audit_id: str
    model_versions: dict[str, str]


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


class PipelineContext:
    def __init__(self):
        self.initialized = False
        self.tmp_dir = None
        self.feature_engine = None
        self.detector_predictor = None
        self.verifier_service = None
        self.decision_engine = None
        self.responder = None
        self.action_adapter = None

    def initialize(self):
        if self.initialized:
            return

        customers, orders, txns, returns, chargebacks, devices, addresses = create_synthetic_dataset()
        self.feature_engine = FeatureEngine(
            transactions=txns,
            orders=orders,
            returns=returns,
            chargebacks=chargebacks,
            customers=customers,
            devices=devices,
            addresses=addresses,
            prediction_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc),
        )

        self.tmp_dir = tempfile.TemporaryDirectory()
        model_path = Path(self.tmp_dir.name)
        train_data = generate_labeled_dataset(num_samples=300, seed=42)
        train_detector(
            train_data,
            model_type="random_forest",
            test_size=0.2,
            val_size=0.2,
            seed=42,
            save_dir=model_path,
        )
        self.detector_predictor = Predictor(model_dir=model_path, model_version="detector-rf-1.0")
        self.verifier_service = VerificationService(feature_engine=self.feature_engine, rule_version="1.0.0")
        self.decision_engine = DecisionEngine.from_policy_file(ROOT / "config" / "merchant_policies.json")
        self.responder = AutoResponder.from_config(template_file=ROOT / "config" / "response_templates.json")
        self.action_adapter = MockActionAdapter(mode="defense_only_simulation")
        self.initialized = True


pipeline_ctx = PipelineContext()


@asynccontextmanager
async def lifespan(app: FastAPI):
    pipeline_ctx.initialize()
    yield


app = FastAPI(
    title="AI Risk Manager API",
    description="Defensive AI Risk Manager REST API for loss detection, verification, cost-aware decisions, and automated responses.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="healthy",
        service="ai-risk-manager",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/risk/analyze", response_model=RiskAnalyzeResponse)
def analyze_risk(req: RiskAnalyzeRequest):
    pipeline_ctx.initialize()

    # Determine timestamp
    txn_timestamp = req.timestamp
    if txn_timestamp is None:
        if req.transaction_id in pipeline_ctx.feature_engine.transactions:
            txn_timestamp = pipeline_ctx.feature_engine.transactions[req.transaction_id].timestamp
        else:
            txn_timestamp = datetime(2026, 8, 23, 11, 30, 0, tzinfo=timezone.utc)

    txn = Transaction(
        transaction_id=req.transaction_id,
        order_id=req.order_id,
        customer_id=req.customer_id,
        amount=req.amount,
        currency=req.currency,
        payment_method=req.payment_method,
        transaction_status=req.transaction_status,
        timestamp=txn_timestamp,
    )

    pipeline_ctx.feature_engine.transactions[txn.transaction_id] = txn

    # 1. Feature Extraction & Detection
    features_dict = extract_detector_features(pipeline_ctx.feature_engine, txn)
    detector_pred = pipeline_ctx.detector_predictor.predict(features_dict)
    detected_case = detector_pred.case_type

    # 2. Specialized Verifier
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
        verifier_case = (
            detected_case
            if detected_case in pipeline_ctx.verifier_service._verifiers
            else "transaction_fraud"
        )
        verifier_result = pipeline_ctx.verifier_service.verify(
            case_type=verifier_case,
            transaction=txn,
            detector_confidence=detector_pred.confidence,
        )

    # 3. Cost-Aware Decision Engine
    decision_result = pipeline_ctx.decision_engine.decide(
        merchant_id=req.merchant_id,
        detector_result=detector_pred,
        verifier_result=verifier_result,
    )

    # 4. Auto-Responder
    response_result = pipeline_ctx.responder.respond(
        decision_result=decision_result,
        event_id=txn.transaction_id,
        input_source=f"{req.merchant_id}_api",
    )

    # 5. Mock Action Execution
    execution_receipt = pipeline_ctx.action_adapter.execute(response_result)

    # 6. Audit Trail Logging
    audit_records = pipeline_ctx.responder.audit_logger.get_by_event_id(txn.transaction_id)
    latest_audit = audit_records[-1] if audit_records else None

    shap_top_features = [
        {
            "feature": f.get("feature", "unknown"),
            "contribution": round(float(f.get("contribution", f.get("abs_contribution", 0.0))), 4),
            "value": round(float(f.get("value", 0.0)), 2),
        }
        for f in (verifier_result.explanation.top_features if verifier_result.explanation else [])
    ]

    return RiskAnalyzeResponse(
        transaction_id=txn.transaction_id,
        merchant_id=req.merchant_id,
        case_type=detected_case,
        detector_confidence=detector_pred.confidence,
        verifier_status=verifier_result.verification_status,
        verifier_risk_score=verifier_result.risk_score,
        evidence_reasons=verifier_result.reasons,
        shap_explanation=shap_top_features,
        decision=decision_result.decision,
        expected_losses=decision_result.expected_loss_by_action,
        selected_expected_loss=decision_result.selected_expected_loss,
        responder_action_code=response_result.action.action_code,
        responder_action_type=response_result.action.action_type,
        defensive_message=response_result.action.message,
        mock_execution_status=execution_receipt.status,
        audit_id=latest_audit.audit_id if latest_audit else "",
        model_versions={
            "detector_model_version": detector_pred.model_version,
            "verifier_model_version": verifier_result.model_version,
            "policy_version": decision_result.policy_name,
        },
    )
