from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional, Any

from risk_manager.responder.types import AuditRecord


class AuditLogger:
    """Thread-safe audit logger for defense-only risk decisions and responses."""

    def __init__(self, log_file: Optional[str | Path] = None):
        self.log_file = Path(log_file) if log_file else None
        self._records: list[AuditRecord] = []
        self._index_by_audit_id: dict[str, AuditRecord] = {}
        self._index_by_event_id: dict[str, list[AuditRecord]] = {}
        self._lock = threading.Lock()

        if self.log_file and self.log_file.parent:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: AuditRecord) -> None:
        with self._lock:
            self._records.append(record)
            self._index_by_audit_id[record.audit_id] = record
            self._index_by_event_id.setdefault(record.event_id, []).append(record)

            if self.log_file:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record.to_dict()) + "\n")

    def get_by_audit_id(self, audit_id: str) -> Optional[AuditRecord]:
        with self._lock:
            return self._index_by_audit_id.get(audit_id)

    def get_by_event_id(self, event_id: str) -> list[AuditRecord]:
        with self._lock:
            return list(self._index_by_event_id.get(event_id, []))

    def record_human_override(
        self,
        audit_id: str,
        reviewer_id: str,
        override_decision: str,
        override_reason: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        with self._lock:
            record = self._index_by_audit_id.get(audit_id)
            if not record:
                return False
            record.human_override = {
                "reviewer_id": reviewer_id,
                "override_decision": override_decision,
                "override_reason": override_reason,
                "metadata": metadata or {},
            }
            return True

    def record_final_outcome(
        self,
        audit_id: str,
        outcome: str,
        chargeback_occurred: bool = False,
        actual_loss_amount: float = 0.0,
        notes: str = "",
    ) -> bool:
        with self._lock:
            record = self._index_by_audit_id.get(audit_id)
            if not record:
                return False
            record.final_outcome = {
                "outcome": outcome,
                "chargeback_occurred": chargeback_occurred,
                "actual_loss_amount": actual_loss_amount,
                "notes": notes,
            }
            return True

    def all_records(self) -> list[AuditRecord]:
        with self._lock:
            return list(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._index_by_audit_id.clear()
            self._index_by_event_id.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)
