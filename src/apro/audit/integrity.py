"""Integrity and completeness validation for Phase 14 audit traces."""

from apro.audit.enums import AuditCompleteness, AuditEventType
from apro.domain.models import AuditEvent


class AuditIntegrityChecker:
    """Validator for causal and referential integrity of case audit trails."""

    @classmethod
    def validate_events_integrity(
        cls,
        case_id: str,
        events: list[AuditEvent],
    ) -> tuple[bool, list[str]]:
        """Validate integrity constraints over an ordered list of audit events."""
        issues: list[str] = []

        if not events:
            issues.append(f"No audit events found for case {case_id}")
            return False, issues

        seen_event_ids: set[str] = set()
        has_execution_started = False
        is_case_closed = False

        for _i, ev in enumerate(events):
            # Check matching case_id
            if ev.case_id != case_id:
                issues.append(
                    f"Event {ev.audit_event_id} has mismatched case_id "
                    f"'{ev.case_id}' (expected '{case_id}')"
                )

            # Check duplicate event ID
            if ev.audit_event_id in seen_event_ids:
                issues.append(f"Duplicate audit_event_id detected: {ev.audit_event_id}")
            seen_event_ids.add(ev.audit_event_id)

            ev_type = ev.event_type

            if ev_type in (
                AuditEventType.EXECUTION_STARTED,
                "EXECUTION_STARTED",
                "EXECUTION_DISPATCHED",
            ):
                has_execution_started = True

            if (
                ev_type
                in (
                    AuditEventType.EXECUTION_COMPLETED,
                    AuditEventType.EXECUTION_FAILED,
                    AuditEventType.EXECUTION_UNKNOWN,
                    "EXECUTION_COMPLETED",
                    "EXECUTION_FAILED",
                )
                and not has_execution_started
            ):
                issues.append(
                    f"Execution completed/failed event {ev.audit_event_id} "
                    "occurred before EXECUTION_STARTED"
                )

            if ev_type in (
                AuditEventType.RECOVERY_CONFIRMED,
                AuditEventType.STOP_DECIDED,
                AuditEventType.ESCALATION_CREATED,
                "CASE_CLOSED",
            ):
                is_case_closed = True
            elif is_case_closed and ev_type in (
                AuditEventType.EXECUTION_STARTED,
                AuditEventType.DECISION_CREATED,
            ):
                issues.append(
                    f"New decision/execution event {ev.audit_event_id} "
                    "occurred after case was closed"
                )

        is_valid = len(issues) == 0
        return is_valid, issues

    @classmethod
    def evaluate_completeness(
        cls,
        has_case: bool,
        has_diagnosis: bool,
        has_decision: bool,
        has_policy: bool,
        has_execution: bool,
        has_outcome: bool,
        is_terminal: bool,
    ) -> AuditCompleteness:
        """Evaluate completeness of a case audit trail."""
        if not has_case:
            return AuditCompleteness.CORRUPT

        if (
            has_case
            and has_diagnosis
            and has_decision
            and has_policy
            and has_execution
            and has_outcome
            and is_terminal
        ):
            return AuditCompleteness.COMPLETE

        return AuditCompleteness.INCOMPLETE
