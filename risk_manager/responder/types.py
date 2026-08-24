from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class ResponseAction:
    action_code: str
    action_type: str
    message: str
    instructions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResponseResult:
    response_id: str
    event_id: str
    merchant_id: str
    decision: str
    case_type: str
    action: ResponseAction
    risk_score: float
    confidence: float
    rationale: list[str]
    is_duplicate: bool = False
    timestamp: str = ""
    audit_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.audit_id:
            self.audit_id = f"audit_{self.response_id}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditRecord:
    audit_id: str
    response_id: str
    event_id: str
    merchant_id: str
    timestamp: str
    input_source: str
    decision: str
    case_type: str
    risk_score: float
    confidence: float
    action_code: str
    action_type: str
    message: str
    instructions: dict[str, Any]
    detector_evidence: dict[str, Any]
    verifier_evidence: dict[str, Any]
    combined_evidence: dict[str, Any]
    rationale: list[str]
    model_versions: dict[str, str]
    rule_versions: dict[str, str]
    policy_version: str
    template_version: str
    is_duplicate: bool
    human_override: dict[str, Any] | None = None
    final_outcome: dict[str, Any] | None = None

    @staticmethod
    def generate_id(prefix: str = "aud") -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
