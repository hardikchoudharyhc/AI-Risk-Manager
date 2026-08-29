from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from risk_manager.decision.policy import PolicyRegistry, MerchantDecisionPolicy, DecisionCosts
from risk_manager.decision.types import ACTIONS, DecisionResult


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def to_canonical_risk_score(val: float | None) -> float:
    """
    Converts 0-1 scale risk score to canonical 0-100 scale score exactly once at the risk-engine boundary.
    0.0    -> 0
    0.3    -> 30
    0.5433 -> 54.33
    0.806  -> 80.6
    1.0    -> 100

    If value is already > 1.0 (on 0-100 scale), returns rounded float.
    """
    if val is None:
        return 0.0
    v = float(val)
    if 0.0 < v <= 1.0:
        v = v * 100.0
    elif v < 0.0:
        v = 0.0
    elif v > 100.0:
        v = 100.0

    r = round(v, 4)
    if r == int(r):
        return float(int(r))
    return r


def map_risk_score_to_level_and_decision(score: float) -> tuple[str, str]:
    """
    Maps a risk score (0.0 to 1.0 or 0 to 100) to (risk_level, decision).

    Score Scale:
    0–29   (0.00 – 0.29): Risk Level = LOW,      Decision = ALLOW
    30–59  (0.30 – 0.59): Risk Level = MEDIUM,   Decision = MONITOR
    60–79  (0.60 – 0.79): Risk Level = HIGH,     Decision = MANUAL_REVIEW
    80–100 (0.80 – 1.00): Risk Level = CRITICAL, Decision = BLOCK
    """
    s = to_canonical_risk_score(score)

    if s < 30.0:
        return "LOW", "ALLOW"
    elif s < 60.0:
        return "MEDIUM", "MONITOR"
    elif s < 80.0:
        return "HIGH", "MANUAL_REVIEW"
    else:
        return "CRITICAL", "BLOCK"



@dataclass
class DecisionEngine:
    """Cost-aware decision engine driven by detector + verifier outputs."""

    policy_registry: PolicyRegistry
    detector_weight: float = 0.35
    verifier_weight: float = 0.65

    @staticmethod
    def from_policy_file(
        path: str | Path,
        detector_weight: float = 0.35,
        verifier_weight: float = 0.65,
    ) -> "DecisionEngine":
        return DecisionEngine(
            policy_registry=PolicyRegistry.from_file(Path(path)),
            detector_weight=detector_weight,
            verifier_weight=verifier_weight,
        )

    def decide(
        self,
        merchant_id: str,
        detector_result,
        verifier_result,
    ) -> DecisionResult:
        policy = self.policy_registry.resolve_policy(merchant_id)

        detector_case = getattr(detector_result, "case_type", "unknown")
        detector_conf = _clamp(float(getattr(detector_result, "confidence", 0.0)))
        detector_probs = getattr(detector_result, "probabilities", {}) or {}

        verifier_case = getattr(verifier_result, "case_type", "unknown")
        verifier_risk = _clamp(float(getattr(verifier_result, "risk_score", 0.0)))
        verifier_conf = _clamp(float(getattr(verifier_result, "confidence", 0.0)))
        verifier_status = getattr(verifier_result, "verification_status", "INCONCLUSIVE")
        edge_flags = list(getattr(verifier_result, "edge_flags", []))

        detector_w = (
            policy.thresholds.detector_weight
            if policy.thresholds.detector_weight is not None
            else self.detector_weight
        )
        verifier_w = (
            policy.thresholds.verifier_weight
            if policy.thresholds.verifier_weight is not None
            else self.verifier_weight
        )
        total_w = detector_w + verifier_w

        detector_risk_signal = self._detector_risk_signal(detector_case, detector_probs, detector_conf)
        if total_w > 0:
            combined_risk = _clamp((detector_w * detector_risk_signal + verifier_w * verifier_risk) / total_w)
        else:
            combined_risk = _clamp(0.5 * detector_risk_signal + 0.5 * verifier_risk)

        uncertainty_penalty = 0.0
        if "missing_customer" in edge_flags:
            uncertainty_penalty += 0.10
        if "new_entity_low_history" in edge_flags:
            uncertainty_penalty += 0.08
        if "missing_ml_features" in edge_flags:
            uncertainty_penalty += 0.05

        combined_confidence = _clamp((detector_conf + verifier_conf) / 2.0 - uncertainty_penalty)

        canonical_risk = to_canonical_risk_score(combined_risk)
        risk_level, decision = map_risk_score_to_level_and_decision(canonical_risk)

        case_type = detector_case if detector_case != "unknown" else verifier_case
        expected_loss = self._expected_loss_by_action(
            risk_probability=combined_risk,
            costs=policy.costs,
            case_type=case_type,
        )

        candidate_actions = [decision]

        rationale = self._build_rationale(
            decision=decision,
            risk=canonical_risk,
            confidence=combined_confidence,
            verifier_status=verifier_status,
            candidate_actions=candidate_actions,
            expected_loss=expected_loss,
            policy=policy,
            edge_flags=edge_flags,
        )

        return DecisionResult(
            merchant_id=merchant_id,
            policy_name=policy.name,
            decision=decision,
            risk_score=canonical_risk,
            risk_level=risk_level,
            confidence=combined_confidence,
            expected_loss_by_action=expected_loss,
            selected_expected_loss=expected_loss.get(decision, expected_loss.get("MANUAL_REVIEW", 0.0)),
            rationale=rationale,
            detector_evidence={
                "case_type": detector_case,
                "confidence": detector_conf,
                "probabilities": detector_probs,
                "risk_signal": detector_risk_signal,
            },
            verifier_evidence={
                "case_type": verifier_case,
                "verification_status": verifier_status,
                "risk_score": to_canonical_risk_score(verifier_risk),
                "confidence": verifier_conf,
                "reasons": list(getattr(verifier_result, "reasons", [])),
                "edge_flags": edge_flags,
                "evidence": getattr(verifier_result, "evidence", {}),
            },
            combined_evidence={
                "combined_risk_formula": f"{detector_w}*detector_signal + {verifier_w}*verifier_risk",
                "combined_confidence_formula": "average(detector_confidence, verifier_confidence)-uncertainty_penalty",
                "uncertainty_penalty": uncertainty_penalty,
                "candidate_actions": candidate_actions,
                "detector_weight": detector_w,
                "verifier_weight": verifier_w,
            },
            model_versions={
                "detector_model_version": getattr(detector_result, "model_version", "unknown"),
                "verifier_model_version": getattr(verifier_result, "model_version", "unknown"),
            },
            rule_versions={
                "verifier_rule_version": getattr(verifier_result, "rule_version", "unknown"),
            },
            policy_version=self.policy_registry.version,
            timestamp=DecisionResult.now_iso(),
        )

    def _detector_risk_signal(self, case_type: str, probs: dict[str, float], confidence: float) -> float:
        if probs:
            normal_prob = float(probs.get("normal", 0.0))
            non_normal_risk = _clamp(1.0 - normal_prob)
            case_prob = _clamp(float(probs.get(case_type, confidence)))
            return _clamp(0.5 * non_normal_risk + 0.5 * case_prob)
        return confidence

    def _expected_loss_by_action(
        self,
        risk_probability: float,
        costs: DecisionCosts,
        case_type: str | None = None,
    ) -> dict[str, float]:
        effective_costs = costs.for_case_type(case_type) if hasattr(costs, "for_case_type") else costs

        fp_cost = effective_costs.false_positive_cost
        fn_cost = effective_costs.false_negative_cost
        mr_cost = effective_costs.manual_review_cost
        mr_fn_rate = effective_costs.manual_review_false_negative_rate
        mr_fp_rate = effective_costs.manual_review_false_positive_rate

        # APPROVE / ALLOW: if risky case is approved, loss is FN cost.
        allow_loss = risk_probability * fn_cost

        # BLOCK / DEFENSIVE_ACTION: blocking benign traffic causes FP cost.
        defensive_loss = (1.0 - risk_probability) * fp_cost

        # MANUAL_REVIEW: review cost plus residual FP/FN after review.
        review_loss = (
            mr_cost
            + risk_probability * fn_cost * mr_fn_rate
            + (1.0 - risk_probability) * fp_cost * mr_fp_rate
        )

        monitor_loss = (
            (mr_cost * 0.5)
            + risk_probability * fn_cost * (mr_fn_rate * 1.2)
            + (1.0 - risk_probability) * fp_cost * (mr_fp_rate * 0.5)
        )

        return {
            "ALLOW": round(allow_loss, 6),
            "MONITOR": round(monitor_loss, 6),
            "MANUAL_REVIEW": round(review_loss, 6),
            "BLOCK": round(defensive_loss, 6),
            "APPROVE": round(allow_loss, 6),
            "DEFENSIVE_ACTION": round(defensive_loss, 6),
        }

    def _candidate_actions(
        self,
        risk: float,
        confidence: float,
        verifier_status: str,
        edge_flags: list[str],
        policy: MerchantDecisionPolicy,
    ) -> list[str]:
        thresholds = policy.thresholds

        # Safety-first for uncertainty: default to review unless emergency risk.
        uncertain = confidence < thresholds.min_auto_confidence or len(edge_flags) > 0
        if uncertain:
            if risk >= thresholds.emergency_defensive_risk:
                return ["MANUAL_REVIEW", "DEFENSIVE_ACTION"]
            return ["MANUAL_REVIEW"]

        candidates = ["MANUAL_REVIEW"]

        if risk <= thresholds.approve_max_risk and verifier_status != "VERIFIED_SUSPICIOUS":
            candidates.append("APPROVE")

        if risk >= thresholds.defensive_min_risk or verifier_status == "VERIFIED_SUSPICIOUS":
            candidates.append("DEFENSIVE_ACTION")

        # Guarantee all actions are valid.
        return [a for a in ACTIONS if a in candidates]

    def _build_rationale(
        self,
        decision: str,
        risk: float,
        confidence: float,
        verifier_status: str,
        candidate_actions: list[str],
        expected_loss: dict[str, float],
        policy: MerchantDecisionPolicy,
        edge_flags: list[str],
    ) -> list[str]:
        rationale = [
            f"Policy '{policy.name}' selected with version {self.policy_registry.version}.",
            f"Combined risk score={risk:.4f}, confidence={confidence:.4f}, verifier status={verifier_status}.",
            "Decision minimizes expected loss among allowed actions.",
            (
                f"Expected loss by action: APPROVE={expected_loss['APPROVE']:.2f}, "
                f"MANUAL_REVIEW={expected_loss['MANUAL_REVIEW']:.2f}, "
                f"DEFENSIVE_ACTION={expected_loss['DEFENSIVE_ACTION']:.2f}."
            ),
            f"Candidate actions after policy and uncertainty checks: {', '.join(candidate_actions)}.",
            f"Chosen action: {decision}.",
        ]

        if edge_flags:
            rationale.append(f"Uncertainty safeguards activated due to edge flags: {', '.join(edge_flags)}.")

        return rationale
