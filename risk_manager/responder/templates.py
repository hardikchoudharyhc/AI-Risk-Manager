from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from risk_manager.responder.types import ResponseAction


DEFAULT_TEMPLATES: dict[str, dict[str, dict[str, Any]]] = {
    "APPROVE": {
      "default": {
        "action_code": "STANDARD_APPROVAL",
        "action_type": "ALLOW",
        "message": "Transaction approved under standard policy.",
        "instructions": {
          "allow_fulfillment": True,
          "require_extra_auth": False,
          "flag_for_review": False,
          "rate_limit": False,
        },
      }
    },
    "MANUAL_REVIEW": {
      "return_abuse": {
        "action_code": "FLAG_RETURN_FOR_STAFF_REVIEW",
        "action_type": "QUEUE_MANUAL_REVIEW",
        "message": "Potential return abuse detected. Hold refund pending manual receipt and item verification.",
        "instructions": {
          "allow_fulfillment": False,
          "require_extra_auth": True,
          "flag_for_review": True,
          "review_queue": "return_abuse_analysts",
          "review_priority": "MEDIUM",
        },
      },
      "transaction_fraud": {
        "action_code": "STEP_UP_AUTHENTICATION_AND_REVIEW",
        "action_type": "QUEUE_MANUAL_REVIEW",
        "message": "Suspicious transaction characteristics detected. Require step-up 2FA/3DS authentication.",
        "instructions": {
          "allow_fulfillment": False,
          "require_extra_auth": True,
          "flag_for_review": True,
          "review_queue": "fraud_investigation_team",
          "review_priority": "HIGH",
        },
      },
      "fraud_spike": {
        "action_code": "ALERT_OPS_TEAM_FOR_REVIEW",
        "action_type": "ALERT_AND_QUEUE",
        "message": "Elevated transaction velocity / anomaly pattern detected. Notify security operations.",
        "instructions": {
          "allow_fulfillment": True,
          "require_extra_auth": False,
          "flag_for_review": True,
          "review_queue": "secops_traffic_monitoring",
          "review_priority": "HIGH",
        },
      },
      "abuse_ring": {
        "action_code": "INVESTIGATION_CASE_QUEUE",
        "action_type": "QUEUE_MANUAL_REVIEW",
        "message": "Coordinated multi-account/device linkage detected. Create ring investigation case.",
        "instructions": {
          "allow_fulfillment": False,
          "require_extra_auth": True,
          "flag_for_review": True,
          "review_queue": "abuse_ring_investigators",
          "review_priority": "CRITICAL",
        },
      },
      "default": {
        "action_code": "GENERAL_MANUAL_REVIEW",
        "action_type": "QUEUE_MANUAL_REVIEW",
        "message": "Risk assessment warrants manual evaluation before finalizing.",
        "instructions": {
          "allow_fulfillment": False,
          "require_extra_auth": True,
          "flag_for_review": True,
          "review_queue": "general_risk_queue",
          "review_priority": "MEDIUM",
        },
      },
    },
    "DEFENSIVE_ACTION": {
      "return_abuse": {
        "action_code": "SUSPEND_RETURN_PRIVILEGES",
        "action_type": "DEFENSIVE_CONTROL",
        "message": "High-confidence return abuse. Restrict instant return privileges; require verified drop-off.",
        "instructions": {
          "allow_fulfillment": False,
          "block_transaction": True,
          "restrict_return_method": "IN_PERSON_WITH_ID",
          "notify_merchant_security": True,
        },
      },
      "transaction_fraud": {
        "action_code": "DECLINE_AND_NOTIFY",
        "action_type": "DEFENSIVE_CONTROL",
        "message": "High-confidence transaction fraud. Defensively decline authorization and log event.",
        "instructions": {
          "allow_fulfillment": False,
          "block_transaction": True,
          "advise_customer_action": "CONTACT_ISSUING_BANK",
          "notify_merchant_security": True,
        },
      },
      "fraud_spike": {
        "action_code": "THROTTLE_VELOCITY_AND_ALERT_SECURITY",
        "action_type": "DEFENSIVE_CONTROL",
        "message": "Severe anomaly spike detected. Engage rate limiting and CAPTCHA challenge on gateway.",
        "instructions": {
          "allow_fulfillment": False,
          "block_transaction": False,
          "enable_captcha_challenge": True,
          "rate_limit_ip_range": True,
          "notify_merchant_security": True,
        },
      },
      "abuse_ring": {
        "action_code": "QUARANTINE_LINKED_ENTITIES",
        "action_type": "DEFENSIVE_CONTROL",
        "message": "Organized fraud ring activity detected. Quarantine linked device and payment tokens.",
        "instructions": {
          "allow_fulfillment": False,
          "block_transaction": True,
          "quarantine_entities": True,
          "revoke_promo_benefits": True,
          "notify_merchant_security": True,
        },
      },
      "default": {
        "action_code": "GENERIC_DEFENSIVE_HOLD",
        "action_type": "DEFENSIVE_CONTROL",
        "message": "High risk threshold exceeded. Defensive action taken to prevent loss.",
        "instructions": {
          "allow_fulfillment": False,
          "block_transaction": True,
          "notify_merchant_security": True,
        },
      },
    },
}


class TemplateRegistry:
    """Loads and resolves deterministic defensive response templates."""

    def __init__(
        self,
        templates: dict[str, dict[str, dict[str, Any]]],
        version: str = "1.0.0",
    ):
        self.templates = templates
        self.version = version

    @staticmethod
    def default() -> "TemplateRegistry":
        return TemplateRegistry(templates=DEFAULT_TEMPLATES, version="1.0.0")

    @staticmethod
    def from_file(path: str | Path) -> "TemplateRegistry":
        p = Path(path)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return TemplateRegistry(
            templates=data.get("templates", DEFAULT_TEMPLATES),
            version=data.get("version", "1.0.0"),
        )

    def resolve_action(self, decision: str, case_type: str | None = None) -> ResponseAction:
        decision_key = decision.upper() if decision else "MANUAL_REVIEW"
        if decision_key not in self.templates:
            decision_key = "MANUAL_REVIEW"

        decision_group = self.templates[decision_key]
        case_key = (case_type.lower() if case_type else "default")

        if case_key in decision_group:
            spec = decision_group[case_key]
        elif "default" in decision_group:
            spec = decision_group["default"]
        else:
            # Fallback
            spec = {
                "action_code": f"GENERIC_{decision_key}",
                "action_type": "DEFENSIVE_SAFEGUARD",
                "message": f"Action executed for {decision_key}.",
                "instructions": {"decision": decision_key},
            }

        return ResponseAction(
            action_code=spec["action_code"],
            action_type=spec["action_type"],
            message=spec["message"],
            instructions=dict(spec.get("instructions", {})),
        )
