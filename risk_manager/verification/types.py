from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class RuleEvaluation:
    """Outcome of a single verifier rule."""

    rule_id: str
    description: str
    triggered: bool
    weight: float
    observed_value: float
    threshold: float
    reason: str


@dataclass
class ModelExplanation:
    """Model explanation payload.

    method values:
    - "shap": SHAP values computed
    - "model_coefficients": fallback contribution explanation
    - "unavailable": explanation could not be computed
    """

    method: str
    available: bool
    top_features: list[dict[str, Any]]
    base_value: float | None
    model_output: float | None
    note: str | None = None


@dataclass
class VerificationResult:
    """Standard output contract for specialized verifiers."""

    case_type: str
    verifier_name: str
    verification_status: str
    risk_score: float
    confidence: float
    evidence: dict[str, Any]
    reasons: list[str]
    applicable_rules: list[RuleEvaluation]
    ml_evidence: dict[str, Any]
    historical_evidence: dict[str, Any]
    explanation: ModelExplanation
    model_version: str
    rule_version: str
    edge_flags: list[str]
    timestamp: str

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert result into JSON-serializable dictionary."""
        data = asdict(self)
        data["applicable_rules"] = [asdict(rule) for rule in self.applicable_rules]
        data["explanation"] = asdict(self.explanation)
        return data
