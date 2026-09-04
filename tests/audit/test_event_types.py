"""Tests for machine-readable event types and taxonomy."""

from apro.audit.enums import AuditEventType


def test_required_event_types_present() -> None:
    """All required event types from Phase 14 specification Section 9 are present."""
    required = [
        "CASE_CREATED",
        "CASE_STATE_CHANGED",
        "PAYMENT_EVENT_OBSERVED",
        "PAYMENT_STATE_CHANGED",
        "DIAGNOSIS_CREATED",
        "DIAGNOSIS_USED",
        "PREDICTION_CREATED",
        "PREDICTION_USED",
        "DECISION_CREATED",
        "POLICY_DECISION_CREATED",
        "ACTION_APPROVED",
        "EXECUTION_STARTED",
        "EXECUTION_COMPLETED",
        "EXECUTION_FAILED",
        "EXECUTION_UNKNOWN",
        "OUTCOME_OBSERVED",
        "OUTCOME_PROCESSED",
        "RE_EVALUATION_STARTED",
        "RE_EVALUATION_COMPLETED",
        "HUMAN_APPROVAL_REQUESTED",
        "HUMAN_APPROVAL_GRANTED",
        "HUMAN_APPROVAL_REJECTED",
        "ESCALATION_CREATED",
        "STOP_DECIDED",
        "RECOVERY_CONFIRMED",
        "ERROR_OBSERVED",
        "INTEGRITY_VIOLATION_DETECTED",
        "SECURITY_VIOLATION_DETECTED",
    ]
    for req in required:
        assert hasattr(AuditEventType, req)
        assert getattr(AuditEventType, req).value == req
