from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from data.synthetic.dataset_generator import create_synthetic_dataset
from risk_manager.decision import DecisionEngine
from risk_manager.detector import generate_labeled_dataset, train_detector, Predictor
from risk_manager.demo import extract_detector_features
from risk_manager.features import FeatureEngine
from risk_manager.models import Transaction
from risk_manager.pipeline import ingest_raw_data
from risk_manager.responder import AutoResponder, MockActionAdapter
from risk_manager.security import validate_file_upload, sanitize_display_text
from risk_manager.verification import VerificationService
from risk_manager.verification.types import VerificationResult, ModelExplanation
from risk_manager.integrations import registry, MerchantConnection

ROOT = Path(__file__).parents[2]


# --- UNIFIED API CONTRACT MODELS FOR REACT / FRONTEND ---

class ProcessRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: Any = Field(..., description="Raw CSV string, JSON array, JSON object, or single record dictionary")
    merchant_id: str | None = Field(default=None, description="Optional merchant schema identifier override")


class TransactionRef(BaseModel):
    transaction_id: str
    order_id: str
    customer_id: str
    amount: float
    currency: str
    payment_method: str
    transaction_status: str
    timestamp: str


class RiskAssessment(BaseModel):
    detected_case: str
    detector_confidence: float
    probabilities: dict[str, float]
    verifier_status: str
    verifier_risk_score: float
    evidence_reasons: list[str]
    shap_top_features: list[dict[str, Any]]


class DecisionDetails(BaseModel):
    final_decision: str
    policy: str
    expected_losses_by_action: dict[str, float]
    rationale: list[str]


class ResponseDetails(BaseModel):
    action_code: str
    action_type: str
    defensive_message: str
    execution_status: str


class AuditDetails(BaseModel):
    audit_id: str
    model_version: str
    policy_version: str
    timestamp: str


class ProcessResultItem(BaseModel):
    case_id: str
    transaction: TransactionRef
    risk_assessment: RiskAssessment
    decision: DecisionDetails
    response: ResponseDetails
    audit: AuditDetails


class ProcessSummary(BaseModel):
    total_records: int
    valid_records: int
    rejected_records: int
    duplicate_records: int
    merchant_id: str
    format_detected: str


class QuarantineSummary(BaseModel):
    rejected_count: int
    errors: list[str]


class ProcessResponse(BaseModel):
    request_id: str
    summary: ProcessSummary
    results: list[ProcessResultItem]
    quarantine: QuarantineSummary


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[str] = []


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ConnectRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    merchant_id: str = Field(default="merchant_a", min_length=1, description="Merchant account ID")
    credentials: dict[str, Any] = Field(default_factory=dict, description="Provider auth credentials")


class RazorpayConnectRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key_id: str = Field(..., min_length=1, description="Razorpay Key ID")
    key_secret: str = Field(..., min_length=1, description="Razorpay Key Secret")
    merchant_id: str = Field(default="merchant_razorpay", description="Merchant account identifier")


class RazorpaySyncRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key_id: str | None = Field(default=None, description="Razorpay Key ID if connecting on sync")
    key_secret: str | None = Field(default=None, description="Razorpay Key Secret if connecting on sync")
    connection_id: str | None = Field(default=None, description="Existing active connection ID")
    count: int = Field(default=10, ge=1, le=50, description="Max batch size to fetch")


class RazorpayOutboundRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    connection_id: str | None = Field(default=None, description="Active connection ID")
    results: list[dict[str, Any]] = Field(default_factory=list, description="M1-M9 risk pipeline results")


class SyncResponse(BaseModel):
    connection_id: str
    merchant_id: str
    provider: str
    synced_records: int
    pipeline_results: list[ProcessResultItem]


class WebhookResponse(BaseModel):
    provider: str
    event_id: str
    status: str
    processed_records: int
    pipeline_results: list[ProcessResultItem]


# --- LEGACY CONTRACT MODELS FOR BACKWARD COMPATIBILITY ---

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


# --- PIPELINE CONTEXT ---

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

# CORS Configuration for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- CUSTOM EXCEPTION HANDLERS ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request payload failed validation.",
                "details": details,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = "BAD_REQUEST" if exc.status_code == 400 else ("UNPROCESSABLE_ENTITY" if exc.status_code == 422 else "ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail),
                "details": [],
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred while processing the request.",
                "details": [],
            }
        },
    )


# --- HELPER FUNCTION FOR PIPELINE EVALUATION ---

def _evaluate_transaction(txn: Transaction, merchant_id: str) -> ProcessResultItem:
    pipeline_ctx.initialize()
    pipeline_ctx.feature_engine.transactions[txn.transaction_id] = txn

    features_dict = extract_detector_features(pipeline_ctx.feature_engine, txn)
    detector_pred = pipeline_ctx.detector_predictor.predict(features_dict)
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

    decision_result = pipeline_ctx.decision_engine.decide(
        merchant_id=merchant_id,
        detector_result=detector_pred,
        verifier_result=verifier_result,
    )

    response_result = pipeline_ctx.responder.respond(
        decision_result=decision_result,
        event_id=txn.transaction_id,
        input_source=f"{merchant_id}_api",
    )

    execution_receipt = pipeline_ctx.action_adapter.execute(response_result)

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

    probs = (
        detector_pred.probabilities
        if hasattr(detector_pred, "probabilities") and detector_pred.probabilities
        else {detected_case: detector_pred.confidence}
    )

    rationale_list = (
        decision_result.rationale
        if hasattr(decision_result, "rationale") and decision_result.rationale
        else [f"Decision selected: {decision_result.decision}"]
    )

    return ProcessResultItem(
        case_id=f"case_{txn.transaction_id}",
        transaction=TransactionRef(
            transaction_id=txn.transaction_id,
            order_id=txn.order_id,
            customer_id=txn.customer_id,
            amount=float(txn.amount),
            currency=txn.currency,
            payment_method=txn.payment_method,
            transaction_status=txn.transaction_status,
            timestamp=txn.timestamp.isoformat(),
        ),
        risk_assessment=RiskAssessment(
            detected_case=detected_case,
            detector_confidence=detector_pred.confidence,
            probabilities=probs,
            verifier_status=verifier_result.verification_status,
            verifier_risk_score=verifier_result.risk_score,
            evidence_reasons=verifier_result.reasons,
            shap_top_features=shap_top_features,
        ),
        decision=DecisionDetails(
            final_decision=decision_result.decision,
            policy=decision_result.policy_name,
            expected_losses_by_action=decision_result.expected_loss_by_action,
            rationale=rationale_list,
        ),
        response=ResponseDetails(
            action_code=response_result.action.action_code,
            action_type=response_result.action.action_type,
            defensive_message=response_result.action.message,
            execution_status=execution_receipt.status,
        ),
        audit=AuditDetails(
            audit_id=latest_audit.audit_id if latest_audit else f"aud_{uuid.uuid4().hex[:8]}",
            model_version=detector_pred.model_version,
            policy_version=decision_result.policy_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )


# --- ENDPOINTS ---

@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="healthy",
        service="ai-risk-manager",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/process", response_model=ProcessResponse)
def process_data(req: ProcessRequest):
    pipeline_ctx.initialize()

    raw_data = req.data
    if raw_data is None or (isinstance(raw_data, str) and not raw_data.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input data cannot be empty.",
        )

    # Perform security check if string/bytes data is supplied
    if isinstance(raw_data, (str, bytes)):
        input_bytes = raw_data if isinstance(raw_data, bytes) else raw_data.encode("utf-8")
        is_valid_upload, upload_err = validate_file_upload(input_bytes, "api_payload.json")
        if not is_valid_upload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=upload_err,
            )

    try:
        valid_txns, stats, merchant_id_detected, format_detected = ingest_raw_data(raw_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed input or parsing failure: {str(exc)}",
        ) from exc

    effective_merchant_id = req.merchant_id or merchant_id_detected

    if not valid_txns:
        err_msg = stats.errors[0] if stats.errors else "No valid transaction records found in input data."
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err_msg,
        )

    results = [_evaluate_transaction(txn, effective_merchant_id) for txn in valid_txns]

    req_id = f"req_{uuid.uuid4().hex[:8]}"

    return ProcessResponse(
        request_id=req_id,
        summary=ProcessSummary(
            total_records=stats.total_records,
            valid_records=stats.valid_records,
            rejected_records=stats.invalid_records,
            duplicate_records=stats.duplicate_records,
            merchant_id=effective_merchant_id,
            format_detected=format_detected,
        ),
        results=results,
        quarantine=QuarantineSummary(
            rejected_count=stats.invalid_records,
            errors=[sanitize_display_text(e) for e in stats.errors],
        ),
    )


@app.post("/risk/analyze", response_model=RiskAnalyzeResponse)
def analyze_risk(req: RiskAnalyzeRequest):
    pipeline_ctx.initialize()

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

    features_dict = extract_detector_features(pipeline_ctx.feature_engine, txn)
    detector_pred = pipeline_ctx.detector_predictor.predict(features_dict)
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

    decision_result = pipeline_ctx.decision_engine.decide(
        merchant_id=req.merchant_id,
        detector_result=detector_pred,
        verifier_result=verifier_result,
    )

    response_result = pipeline_ctx.responder.respond(
        decision_result=decision_result,
        event_id=txn.transaction_id,
        input_source=f"{req.merchant_id}_api",
    )

    execution_receipt = pipeline_ctx.action_adapter.execute(response_result)

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


# --- MERCHANT INTEGRATION & WEBHOOK ENDPOINTS ---

@app.get("/integrations")
def list_integrations():
    return registry.list_providers()


@app.post("/integrations/razorpay/connect")
def connect_razorpay(req: RazorpayConnectRequest):
    provider_inst = registry.get_provider("razorpay")
    if not provider_inst:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay provider integration not registered.",
        )
    try:
        conn = provider_inst.authenticate(
            merchant_id=req.merchant_id,
            credentials={"key_id": req.key_id, "key_secret": req.key_secret},
        )
        registry.add_connection(conn)
        res_dict = conn.safe_dict()
        res_dict["message"] = "Successfully authenticated with Razorpay API."
        return res_dict
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Razorpay connection failed: {str(exc)}",
        ) from exc


@app.post("/integrations/razorpay/sync", response_model=SyncResponse)
def sync_razorpay(req: RazorpaySyncRequest):
    pipeline_ctx.initialize()
    provider_inst = registry.get_provider("razorpay")
    if not provider_inst:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay provider integration not registered.",
        )

    conn = None
    if req.connection_id:
        conn = registry.get_connection(req.connection_id)

    if not conn and req.key_id and req.key_secret:
        try:
            conn = provider_inst.authenticate(
                merchant_id="merchant_razorpay",
                credentials={"key_id": req.key_id, "key_secret": req.key_secret},
            )
            registry.add_connection(conn)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Razorpay authentication failed: {str(exc)}",
            ) from exc

    if not conn:
        conns = registry.list_connections()
        rzp_conns = [c for c in conns if c.provider == "razorpay"]
        if rzp_conns:
            conn = rzp_conns[-1]

    if not conn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active Razorpay connection found. Provide key_id and key_secret or connection_id.",
        )

    try:
        valid_txns, stats = provider_inst.sync_transactions(conn)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Razorpay sync failed: {str(exc)}",
        ) from exc

    results = [_evaluate_transaction(txn, conn.merchant_id) for txn in valid_txns]

    return SyncResponse(
        connection_id=conn.connection_id,
        merchant_id=conn.merchant_id,
        provider="razorpay",
        synced_records=len(valid_txns),
        pipeline_results=results,
    )


@app.post("/integrations/razorpay/outbound")
def send_razorpay_outbound(req: RazorpayOutboundRequest):
    provider_inst = registry.get_provider("razorpay")
    if not provider_inst:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay provider integration not registered.",
        )

    conn = None
    if req.connection_id:
        conn = registry.get_connection(req.connection_id)

    if not conn:
        conns = registry.list_connections()
        rzp_conns = [c for c in conns if c.provider == "razorpay"]
        if rzp_conns:
            conn = rzp_conns[-1]

    if not conn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active Razorpay connection found for outbound dispatch.",
        )

    try:
        ack_batch = provider_inst.send_batch_risk_results(conn, req.results)
        return ack_batch
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Outbound dispatch failed: {str(exc)}",
        ) from exc


@app.post("/integrations/{provider}/connect")
def connect_provider(provider: str, req: ConnectRequest):
    provider_inst = registry.get_provider(provider)
    if not provider_inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration provider '{provider}' is not supported.",
        )
    try:
        combined_creds = {**req.model_dump(), **(req.credentials or {})}
        conn = provider_inst.authenticate(req.merchant_id, combined_creds)
        registry.add_connection(conn)
        return conn.safe_dict()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection failed: {str(exc)}",
        ) from exc


@app.get("/integrations/{connection_id}")
def get_connection(connection_id: str):
    conn = registry.get_connection(connection_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection ID '{connection_id}' not found.",
        )
    return conn.safe_dict()


@app.post("/integrations/{connection_id}/sync", response_model=SyncResponse)
def sync_connection(connection_id: str):
    pipeline_ctx.initialize()
    conn = registry.get_connection(connection_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection ID '{connection_id}' not found.",
        )
    provider_inst = registry.get_provider(conn.provider)
    if not provider_inst:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Provider '{conn.provider}' not registered.",
        )
    try:
        valid_txns, stats = provider_inst.sync_transactions(conn)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sync failed: {str(exc)}",
        ) from exc

    results = [_evaluate_transaction(txn, conn.merchant_id) for txn in valid_txns]

    return SyncResponse(
        connection_id=conn.connection_id,
        merchant_id=conn.merchant_id,
        provider=conn.provider,
        synced_records=len(valid_txns),
        pipeline_results=results,
    )


@app.post("/webhooks/{provider}", response_model=WebhookResponse)
async def receive_webhook(provider: str, request: Request):
    pipeline_ctx.initialize()
    provider_inst = registry.get_provider(provider)
    if not provider_inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook provider '{provider}' is not supported.",
        )

    payload = await request.body()
    headers = dict(request.headers)

    webhook_secret = headers.get("x-webhook-secret") or ""
    if webhook_secret and not provider_inst.verify_webhook(payload, headers, webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook signature verification failed.",
        )

    try:
        records, event_id = provider_inst.parse_webhook_event(payload, headers)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook parse failure: {str(exc)}",
        ) from exc

    if registry.dedup_cache.is_duplicate(event_id):
        return WebhookResponse(
            provider=provider,
            event_id=event_id,
            status="duplicate_skipped",
            processed_records=0,
            pipeline_results=[],
        )

    registry.dedup_cache.mark_seen(event_id)

    valid_txns, stats, merchant_detected, _ = ingest_raw_data(records)
    results = [_evaluate_transaction(txn, merchant_detected or provider) for txn in valid_txns]

    return WebhookResponse(
        provider=provider,
        event_id=event_id,
        status="processed",
        processed_records=len(valid_txns),
        pipeline_results=results,
    )

