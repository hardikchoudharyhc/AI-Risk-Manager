from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
import uuid

from risk_manager.responder.types import ResponseResult


@dataclass
class MockExecutionReceipt:
    execution_id: str
    response_id: str
    event_id: str
    merchant_id: str
    action_code: str
    action_type: str
    status: str
    simulated: bool
    executed_steps: list[str]
    external_reference_ids: dict[str, str]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MockActionAdapter:
    """Safe, defense-only mock action adapter simulating external execution."""

    def __init__(self, mode: str = "mock"):
        self.mode = mode

    def execute(self, response: ResponseResult) -> MockExecutionReceipt:
        """Execute simulated defensive action without external network calls."""
        action = response.action
        code = action.action_code
        instr = action.instructions or {}
        exec_id = f"exec_{uuid.uuid4().hex[:10]}"
        steps: list[str] = []
        ext_refs: dict[str, str] = {}

        if code == "STANDARD_APPROVAL":
            steps.append("Payment Gateway: Capture and fulfill transaction authorization.")
            ext_refs["gateway_capture_id"] = f"cap_{uuid.uuid4().hex[:8]}"
            steps.append("Fulfillment Service: Released order to warehouse packing queue.")

        elif code == "FLAG_RETURN_FOR_STAFF_REVIEW":
            ticket_id = f"tkt_ra_{uuid.uuid4().hex[:8]}"
            steps.append(f"Returns Portal: Held instant refund; generated return drop-off barcode.")
            steps.append(f"Case Management: Created ticket {ticket_id} in queue '{instr.get('review_queue', 'return_analysts')}'.")
            ext_refs["case_ticket_id"] = ticket_id

        elif code == "STEP_UP_AUTHENTICATION_AND_REVIEW":
            auth_challenge_id = f"chal_3ds_{uuid.uuid4().hex[:8]}"
            steps.append(f"3DS / Identity Provider: Dispatched step-up OTP challenge ({auth_challenge_id}).")
            steps.append(f"Fraud Queue: Created high-priority manual review case in '{instr.get('review_queue', 'fraud_team')}'.")
            ext_refs["challenge_id"] = auth_challenge_id

        elif code == "ALERT_OPS_TEAM_FOR_REVIEW":
            alert_id = f"alert_secops_{uuid.uuid4().hex[:8]}"
            steps.append(f"Monitoring Dashboard: Triggered real-time velocity spike notification ({alert_id}).")
            steps.append(f"SecOps Pager: Dispatched anomaly alert to '{instr.get('review_queue', 'secops')}'.")
            ext_refs["secops_alert_id"] = alert_id

        elif code == "INVESTIGATION_CASE_QUEUE":
            ring_case_id = f"case_ring_{uuid.uuid4().hex[:8]}"
            steps.append(f"Graph Intelligence: Clustered linked accounts and devices into investigation case {ring_case_id}.")
            steps.append("Account Security: Applied provisional review hold on linked withdrawal/payout operations.")
            ext_refs["investigation_case_id"] = ring_case_id

        elif code == "SUSPEND_RETURN_PRIVILEGES":
            steps.append("Policy Enforcement: Suspended unverified online return requests for customer.")
            steps.append("Customer Communication: Sent instructions for in-person verified return.")
            ext_refs["policy_enforcement_id"] = f"enf_{uuid.uuid4().hex[:8]}"

        elif code == "DECLINE_AND_NOTIFY":
            decline_code = "DEFENSIVE_BLOCK_SUSPECTED_FRAUD"
            steps.append(f"Payment Gateway: Safely declined authorization code: {decline_code}.")
            steps.append("Customer Messaging: Sent advisory notification to contact issuing bank.")
            ext_refs["gateway_decline_ref"] = f"dec_{uuid.uuid4().hex[:8]}"

        elif code == "THROTTLE_VELOCITY_AND_ALERT_SECURITY":
            steps.append("Gateway WAF: Enacted temporary IP rate-limiting and CAPTCHA challenge.")
            steps.append("Incident Management: Opened automated P1 SecOps incident.")
            ext_refs["incident_id"] = f"inc_{uuid.uuid4().hex[:8]}"

        elif code == "QUARANTINE_LINKED_ENTITIES":
            steps.append("Token Vault: Quarantined shared device tokens and payment instruments.")
            steps.append("Promo Engine: Revoked active promotional abuse vouchers.")
            ext_refs["quarantine_batch_id"] = f"qtn_{uuid.uuid4().hex[:8]}"

        else:
            steps.append(f"Safeguard Controller: Executed default defensive action '{code}'.")
            ext_refs["safeguard_ref"] = f"safe_{uuid.uuid4().hex[:8]}"

        return MockExecutionReceipt(
            execution_id=exec_id,
            response_id=response.response_id,
            event_id=response.event_id,
            merchant_id=response.merchant_id,
            action_code=code,
            action_type=action.action_type,
            status="SUCCESS",
            simulated=True,
            executed_steps=steps,
            external_reference_ids=ext_refs,
        )
