"""Unit tests for domain entity models and immutability semantics."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

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
from apro.domain.models import (
    ActionEvaluation,
    AuditEvent,
    Customer,
    Decision,
    Diagnosis,
    Execution,
    Outcome,
    Payment,
    PaymentEvent,
    PolicyDecision,
    RecoveryAction,
    RecoveryCase,
)


def test_customer_model() -> None:
    now = datetime.now(UTC)
    cust = Customer(
        customer_id="cust_123",
        external_reference="ref_ext_123",
        created_at=now,
        updated_at=now,
    )
    assert cust.customer_id == "cust_123"
    assert cust.historical_payment_count == 0

    # Mutable check
    cust.historical_payment_count = 5
    assert cust.historical_payment_count == 5


def test_payment_model() -> None:
    now = datetime.now(UTC)
    pay = Payment(
        payment_id="pay_123",
        customer_id="cust_123",
        order_id="order_123",
        provider="razorpay",
        amount=5000,
        currency="INR",
        method="card",
        status=PaymentStatus.CREATED,
        created_at=now,
        updated_at=now,
    )
    assert pay.payment_id == "pay_123"
    assert pay.status == PaymentStatus.CREATED

    # Mutable status update check via model copy/update or direct attribute
    pay.status = PaymentStatus.FAILED
    assert pay.status == PaymentStatus.FAILED


def test_recovery_case_model() -> None:
    now = datetime.now(UTC)
    case = RecoveryCase(
        case_id="case_123",
        payment_id="pay_123",
        customer_id="cust_123",
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
    )
    assert case.case_id == "case_123"
    assert case.status == RecoveryCaseStatus.NEW


def test_recovery_action_model() -> None:
    now = datetime.now(UTC)
    action = RecoveryAction(
        action_id="act_123",
        case_id="case_123",
        action_type=RecoveryActionType.RETRY,
        status=RecoveryActionStatus.CANDIDATE,
        created_at=now,
        updated_at=now,
        parameters={"discount": 10},
    )
    assert action.action_id == "act_123"
    assert action.parameters == {"discount": 10}


def test_execution_model() -> None:
    now = datetime.now(UTC)
    exec_obj = Execution(
        execution_id="exec_123",
        action_id="act_123",
        case_id="case_123",
        execution_type="standard_retry",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        status=ExecutionStatus.PENDING,
        started_at=now,
    )
    assert exec_obj.execution_id == "exec_123"
    assert exec_obj.execution_type == "standard_retry"


def test_payment_event_immutability() -> None:
    now = datetime.now(UTC)
    event = PaymentEvent(
        event_id="evt_123",
        provider="razorpay",
        event_type="payment.failed",
        payment_id="pay_123",
        amount=5000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        event_timestamp=now,
        received_at=now,
    )
    assert event.event_id == "evt_123"

    with pytest.raises(ValidationError):
        event.status = PaymentStatus.CAPTURED  # type: ignore[misc]


def test_diagnosis_immutability() -> None:
    now = datetime.now(UTC)
    diag = Diagnosis(
        diagnosis_id="diag_123",
        case_id="case_123",
        category=FailureCategory.TRANSIENT,
        confidence=0.85,
        evidence=("gateway_timeout", "recent_success"),
        model_name="rules_engine",
        model_version="1.0.0",
        created_at=now,
    )
    assert diag.confidence == 0.85

    with pytest.raises(ValidationError):
        diag.confidence = 0.99  # type: ignore[misc]


def test_action_evaluation_immutability() -> None:
    now = datetime.now(UTC)
    eval_obj = ActionEvaluation(
        evaluation_id="eval_123",
        case_id="case_123",
        action_type=RecoveryActionType.RETRY,
        success_probability=0.75,
        recoverable_amount=5000,
        action_cost=100,
        expected_recovery_value=3650,
        model_name="economic_evaluator",
        model_version="1.0.0",
        created_at=now,
    )
    assert eval_obj.expected_recovery_value == 3650

    with pytest.raises(ValidationError):
        eval_obj.action_cost = 50  # type: ignore[misc]


def test_decision_immutability() -> None:
    now = datetime.now(UTC)
    dec = Decision(
        decision_id="dec_123",
        case_id="case_123",
        recommended_action=RecoveryActionType.RETRY,
        confidence=0.85,
        expected_recovery_value=3650,
        reason="Highest ERV action",
        model_name="llm_agent",
        model_version="1.0.0",
        created_at=now,
    )
    assert dec.recommended_action == RecoveryActionType.RETRY

    with pytest.raises(ValidationError):
        dec.reason = "Mutated reason"  # type: ignore[misc]


def test_policy_decision_immutability() -> None:
    now = datetime.now(UTC)
    pdec = PolicyDecision(
        policy_decision_id="pdec_123",
        decision_id="dec_123",
        case_id="case_123",
        result=PolicyDecisionResult.ALLOW,
        reason="Within policy bounds",
        policy_version="1.0.0",
        created_at=now,
    )
    assert pdec.result == PolicyDecisionResult.ALLOW

    with pytest.raises(ValidationError):
        pdec.result = PolicyDecisionResult.BLOCK  # type: ignore[misc]


def test_outcome_immutability() -> None:
    now = datetime.now(UTC)
    out = Outcome(
        outcome_id="out_123",
        case_id="case_123",
        execution_id="exec_123",
        type=OutcomeType.RECOVERED,
        amount_recovered=5000,
        observed_at=now,
    )
    assert out.amount_recovered == 5000

    with pytest.raises(ValidationError):
        out.amount_recovered = 0  # type: ignore[misc]


def test_audit_event_immutability() -> None:
    now = datetime.now(UTC)
    audit = AuditEvent(
        audit_event_id="aud_123",
        case_id="case_123",
        event_type="CASE_CREATED",
        actor=AuditActor.SYSTEM,
        timestamp=now,
        payload={"action": "create"},
    )
    assert audit.actor == AuditActor.SYSTEM

    with pytest.raises(ValidationError):
        audit.event_type = "CASE_STOPPED"  # type: ignore[misc]
