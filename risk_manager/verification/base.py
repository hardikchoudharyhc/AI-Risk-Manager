from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from risk_manager.verification.ml_explainer import MLEvidenceModel
from risk_manager.verification.types import RuleEvaluation, VerificationResult


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class BaseVerifier(ABC):
    """Shared orchestration for class-specific verifiers."""

    def __init__(
        self,
        verifier_name: str,
        case_type: str,
        rule_version: str,
        model_version: str,
        ml_feature_names: list[str],
        ml_feature_ranges: dict[str, tuple[float, float]],
        ml_feature_weights: dict[str, float],
    ):
        self.verifier_name = verifier_name
        self.case_type = case_type
        self.rule_version = rule_version
        self.model_version = model_version
        self.ml_model = MLEvidenceModel(
            feature_names=ml_feature_names,
            feature_ranges=ml_feature_ranges,
            feature_weights=ml_feature_weights,
            model_version=model_version,
        )

    @abstractmethod
    def _evaluate_rules(
        self,
        feature_map: dict[str, Any],
        history: dict[str, Any],
    ) -> list[RuleEvaluation]:
        """Evaluate class-specific rules."""

    @abstractmethod
    def _historical_score(self, feature_map: dict[str, Any], history: dict[str, Any]) -> float:
        """Compute historical evidence score in [0, 1]."""

    def verify(
        self,
        feature_obj,
        history: dict[str, Any],
        detector_confidence: float = 0.0,
    ) -> VerificationResult:
        feature_map = feature_obj.to_dict()

        rules = self._evaluate_rules(feature_map, history)
        rule_score = self._rule_score(rules)

        ml_result = self.ml_model.score_and_explain(feature_map)
        historical_score = clamp(self._historical_score(feature_map, history))

        risk_score = clamp(
            0.45 * rule_score +
            0.35 * ml_result.score +
            0.20 * historical_score
        )

        confidence = 0.55 + abs(risk_score - 0.5) * 0.6
        if detector_confidence > 0:
            confidence = 0.65 * confidence + 0.35 * clamp(detector_confidence)

        edge_flags = list(history.get("edge_flags", []))
        if history.get("new_or_low_history", False):
            confidence -= 0.15
        if history.get("missing_customer", False):
            confidence -= 0.1
        if ml_result.missing_features:
            confidence -= 0.05
            edge_flags.append("missing_ml_features")

        confidence = clamp(confidence)

        if risk_score >= 0.75:
            status = "VERIFIED_SUSPICIOUS"
        elif risk_score <= 0.35:
            status = "VERIFIED_NOT_SUSPICIOUS"
        else:
            status = "INCONCLUSIVE"

        reasons = self._build_reasons(rules, ml_result.explanation.top_features, history)

        evidence = {
            "feature_snapshot": feature_map,
            "rule_score": rule_score,
            "historical_score": historical_score,
            "detector_confidence": clamp(detector_confidence),
            "missing_ml_features": ml_result.missing_features,
        }

        ml_evidence = {
            "ml_score": ml_result.score,
            "model_type": "logistic_regression",
            "model_version": self.model_version,
            "missing_feature_count": len(ml_result.missing_features),
        }

        historical_evidence = {
            "prior_order_count": history.get("prior_order_count", 0),
            "prior_transaction_count": history.get("prior_transaction_count", 0),
            "prior_return_count": history.get("prior_return_count", 0),
            "prior_chargeback_count": history.get("prior_chargeback_count", 0),
            "new_or_low_history": history.get("new_or_low_history", False),
        }

        return VerificationResult(
            case_type=self.case_type,
            verifier_name=self.verifier_name,
            verification_status=status,
            risk_score=risk_score,
            confidence=confidence,
            evidence=evidence,
            reasons=reasons,
            applicable_rules=rules,
            ml_evidence=ml_evidence,
            historical_evidence=historical_evidence,
            explanation=ml_result.explanation,
            model_version=self.model_version,
            rule_version=self.rule_version,
            edge_flags=edge_flags,
            timestamp=VerificationResult.now_iso(),
        )

    def _rule_score(self, rules: list[RuleEvaluation]) -> float:
        if not rules:
            return 0.0
        total_weight = sum(max(0.0, rule.weight) for rule in rules)
        if total_weight <= 0:
            return 0.0
        triggered_weight = sum(rule.weight for rule in rules if rule.triggered)
        return clamp(triggered_weight / total_weight)

    def _build_reasons(
        self,
        rules: list[RuleEvaluation],
        top_features: list[dict[str, Any]],
        history: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []

        for rule in rules:
            if rule.triggered:
                reasons.append(rule.reason)

        for item in top_features[:2]:
            feature = item.get("feature", "unknown")
            contribution = float(item.get("contribution", 0.0))
            direction = "increased" if contribution >= 0 else "reduced"
            reasons.append(f"Model evidence: {feature} {direction} risk contribution ({contribution:.3f}).")

        if history.get("new_or_low_history", False):
            reasons.append("Limited historical evidence available; confidence adjusted.")

        return reasons[:6]
