from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DecisionThresholds:
    approve_max_risk: float
    defensive_min_risk: float
    min_auto_confidence: float
    emergency_defensive_risk: float
    detector_weight: float | None = None
    verifier_weight: float | None = None


@dataclass
class DecisionCosts:
    false_positive_cost: float
    false_negative_cost: float
    manual_review_cost: float
    manual_review_false_negative_rate: float
    manual_review_false_positive_rate: float
    case_costs: dict[str, dict[str, float]] = field(default_factory=dict)

    def for_case_type(self, case_type: str | None) -> "DecisionCosts":
        if not case_type or not self.case_costs or case_type not in self.case_costs:
            return self
        overrides = self.case_costs[case_type]
        return DecisionCosts(
            false_positive_cost=float(overrides.get("false_positive_cost", self.false_positive_cost)),
            false_negative_cost=float(overrides.get("false_negative_cost", self.false_negative_cost)),
            manual_review_cost=float(overrides.get("manual_review_cost", self.manual_review_cost)),
            manual_review_false_negative_rate=float(
                overrides.get("manual_review_false_negative_rate", self.manual_review_false_negative_rate)
            ),
            manual_review_false_positive_rate=float(
                overrides.get("manual_review_false_positive_rate", self.manual_review_false_positive_rate)
            ),
            case_costs=self.case_costs,
        )

    def get_false_positive_cost(self, case_type: str | None = None) -> float:
        return self.for_case_type(case_type).false_positive_cost

    def get_false_negative_cost(self, case_type: str | None = None) -> float:
        return self.for_case_type(case_type).false_negative_cost

    def get_manual_review_cost(self, case_type: str | None = None) -> float:
        return self.for_case_type(case_type).manual_review_cost


@dataclass
class MerchantDecisionPolicy:
    name: str
    thresholds: DecisionThresholds
    costs: DecisionCosts


class PolicyRegistry:
    """Policy loader and merchant-policy resolver."""

    def __init__(
        self,
        policies: dict[str, MerchantDecisionPolicy],
        default_policy: str,
        merchant_policy_map: dict[str, str],
        version: str,
    ):
        self.policies = policies
        self.default_policy = default_policy
        self.merchant_policy_map = merchant_policy_map
        self.version = version

    def resolve_policy(self, merchant_id: str) -> MerchantDecisionPolicy:
        policy_name = self.merchant_policy_map.get(merchant_id, self.default_policy)
        if policy_name not in self.policies:
            policy_name = self.default_policy
        return self.policies[policy_name]

    @staticmethod
    def from_file(path: Path) -> "PolicyRegistry":
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        policy_map: dict[str, MerchantDecisionPolicy] = {}
        for name, p in payload["policies"].items():
            thresholds = DecisionThresholds(**p["thresholds"])
            costs_data = dict(p["costs"])
            case_costs = (
                costs_data.pop("case_costs", {})
                or costs_data.pop("case_type_costs", {})
                or costs_data.pop("by_case_type", {})
            )
            costs = DecisionCosts(**costs_data, case_costs=case_costs)
            policy_map[name] = MerchantDecisionPolicy(name=name, thresholds=thresholds, costs=costs)

        return PolicyRegistry(
            policies=policy_map,
            default_policy=payload["default_policy"],
            merchant_policy_map=payload.get("merchant_policy_map", {}),
            version=payload.get("version", "unknown"),
        )
