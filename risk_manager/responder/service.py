from __future__ import annotations

from pathlib import Path
from typing import Optional, Any
import uuid

from risk_manager.decision.types import DecisionResult
from risk_manager.responder.audit import AuditLogger
from risk_manager.responder.idempotency import IdempotencyStore
from risk_manager.responder.templates import TemplateRegistry
from risk_manager.responder.types import ResponseResult, AuditRecord, ResponseAction


class AutoResponder:
    """Automated, defense-only response orchestration layer."""

    def __init__(
        self,
        template_registry: Optional[TemplateRegistry] = None,
        idempotency_store: Optional[IdempotencyStore] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.template_registry = template_registry if template_registry is not None else TemplateRegistry.default()
        self.idempotency_store = idempotency_store if idempotency_store is not None else IdempotencyStore()
        self.audit_logger = audit_logger if audit_logger is not None else AuditLogger()

    @staticmethod
    def from_config(
        template_file: str | Path,
        log_file: Optional[str | Path] = None,
    ) -> "AutoResponder":
        registry = TemplateRegistry.from_file(template_file)
        logger = AuditLogger(log_file=log_file)
        return AutoResponder(template_registry=registry, audit_logger=logger)

    def respond(
        self,
        decision_result: DecisionResult,
        event_id: Optional[str] = None,
        input_source: str = "canonical_pipeline",
        metadata: Optional[dict[str, Any]] = None,
    ) -> ResponseResult:
        """Execute automated defensive response based strictly on decision output."""
        merchant_id = decision_result.merchant_id
        ev_id = event_id or f"evt_{uuid.uuid4().hex[:10]}"

        # 1. Idempotency check: prevent duplicate execution
        cached = self.idempotency_store.get(merchant_id, ev_id)
        if cached is not None:
            # Return cached response flagged as duplicate
            return ResponseResult(
                response_id=cached.response_id,
                event_id=cached.event_id,
                merchant_id=cached.merchant_id,
                decision=cached.decision,
                case_type=cached.case_type,
                action=cached.action,
                risk_score=cached.risk_score,
                confidence=cached.confidence,
                rationale=cached.rationale,
                is_duplicate=True,
                timestamp=cached.timestamp,
                audit_id=cached.audit_id,
            )

        # 2. Extract case type and decision (strictly consume decision engine output)
        detector_ev = decision_result.detector_evidence or {}
        verifier_ev = decision_result.verifier_evidence or {}

        case_type = (
            detector_ev.get("case_type")
            or verifier_ev.get("case_type")
            or "unknown"
        )
        decision = decision_result.decision

        # 3. Resolve deterministic defensive action template
        action: ResponseAction = self.template_registry.resolve_action(
            decision=decision,
            case_type=case_type,
        )

        response_id = f"resp_{uuid.uuid4().hex[:12]}"
        audit_id = f"aud_{uuid.uuid4().hex[:12]}"

        # 4. Construct response result
        result = ResponseResult(
            response_id=response_id,
            event_id=ev_id,
            merchant_id=merchant_id,
            decision=decision,
            case_type=case_type,
            action=action,
            risk_score=decision_result.risk_score,
            confidence=decision_result.confidence,
            rationale=list(decision_result.rationale),
            is_duplicate=False,
            audit_id=audit_id,
        )

        # 5. Construct and write complete audit record
        audit_record = AuditRecord(
            audit_id=audit_id,
            response_id=response_id,
            event_id=ev_id,
            merchant_id=merchant_id,
            timestamp=result.timestamp,
            input_source=input_source,
            decision=decision,
            case_type=case_type,
            risk_score=decision_result.risk_score,
            confidence=decision_result.confidence,
            action_code=action.action_code,
            action_type=action.action_type,
            message=action.message,
            instructions=action.instructions,
            detector_evidence=detector_ev,
            verifier_evidence=verifier_ev,
            combined_evidence=decision_result.combined_evidence or {},
            rationale=list(decision_result.rationale),
            model_versions=decision_result.model_versions or {},
            rule_versions=decision_result.rule_versions or {},
            policy_version=decision_result.policy_version,
            template_version=self.template_registry.version,
            is_duplicate=False,
        )

        self.audit_logger.log(audit_record)
        self.idempotency_store.set(merchant_id, ev_id, result)

        return result
