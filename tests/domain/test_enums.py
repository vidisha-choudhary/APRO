"""Unit tests for domain enums and vocabularies."""

from apro.domain.enums import (
    AuditActor,
    ExecutionMode,
    ExecutionStatus,
    FailureCategory,
    OutcomeType,
    PaymentStatus,
    PolicyDecisionResult,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)


def test_payment_status_vocabulary() -> None:
    expected = {"CREATED", "AUTHORIZED", "CAPTURED", "FAILED", "PENDING"}
    actual = {s.value for s in PaymentStatus}
    assert actual == expected


def test_recovery_case_status_vocabulary() -> None:
    expected = {
        "NEW",
        "DIAGNOSING",
        "EVALUATING",
        "DECISION_PENDING",
        "POLICY_CHECK",
        "ACTION_APPROVED",
        "EXECUTING",
        "OBSERVING",
        "RECOVERED",
        "STOPPED",
        "ESCALATED",
    }
    actual = {s.value for s in RecoveryCaseStatus}
    assert actual == expected


def test_recovery_action_type_vocabulary() -> None:
    expected = {"RETRY", "ALTERNATE_RECOVERY", "OUTREACH", "ESCALATE", "STOP"}
    actual = {a.value for a in RecoveryActionType}
    assert actual == expected


def test_recovery_action_status_vocabulary() -> None:
    expected = {
        "CANDIDATE",
        "RECOMMENDED",
        "APPROVED",
        "BLOCKED",
        "EXECUTING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
    }
    actual = {s.value for s in RecoveryActionStatus}
    assert actual == expected


def test_policy_decision_result_vocabulary() -> None:
    expected = {"ALLOW", "BLOCK", "REQUIRE_HUMAN_APPROVAL"}
    actual = {r.value for r in PolicyDecisionResult}
    assert actual == expected


def test_execution_status_vocabulary() -> None:
    expected = {
        "PENDING",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
        "UNKNOWN",
        "CANCELLED",
    }
    actual = {s.value for s in ExecutionStatus}
    assert actual == expected


def test_execution_mode_vocabulary() -> None:
    expected = {"RAZORPAY_TEST_MODE", "SIMULATION", "INTERNAL"}
    actual = {m.value for m in ExecutionMode}
    assert actual == expected


def test_outcome_type_vocabulary() -> None:
    expected = {
        "RECOVERED",
        "FAILED",
        "PENDING",
        "EXPIRED",
        "STOPPED",
        "ESCALATED",
    }
    actual = {t.value for t in OutcomeType}
    assert actual == expected


def test_audit_actor_vocabulary() -> None:
    expected = {
        "SYSTEM",
        "MODEL",
        "POLICY",
        "EXECUTOR",
        "HUMAN",
        "RAZORPAY",
        "SIMULATOR",
    }
    actual = {a.value for a in AuditActor}
    assert actual == expected


def test_failure_category_vocabulary() -> None:
    expected = {
        "TRANSIENT",
        "BANK_SIDE",
        "CUSTOMER_SIDE",
        "AUTHENTICATION",
        "PAYMENT_METHOD",
        "GATEWAY",
        "TIMEOUT",
        "UNKNOWN",
    }
    actual = {c.value for c in FailureCategory}
    assert actual == expected
