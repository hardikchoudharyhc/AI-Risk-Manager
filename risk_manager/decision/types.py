from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


ACTIONS = ("APPROVE", "MANUAL_REVIEW", "DEFENSIVE_ACTION")


@dataclass
class DecisionResult:
    merchant_id: str
    policy_name: str
    decision: str
    risk_score: float
    confidence: float
    expected_loss_by_action: dict[str, float]
    selected_expected_loss: float
    rationale: list[str]
    detector_evidence: dict[str, Any]
    verifier_evidence: dict[str, Any]
    combined_evidence: dict[str, Any]
    model_versions: dict[str, str]
    rule_versions: dict[str, str]
    policy_version: str
    timestamp: str

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
