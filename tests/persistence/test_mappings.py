"""Unit tests for domain <-> ORM model mapping functions."""

import uuid
from datetime import UTC, datetime

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
from apro.persistence.mapper import (
    action_evaluation_to_domain,
    action_evaluation_to_orm,
    audit_event_to_domain,
    audit_event_to_orm,
    customer_to_domain,
    customer_to_orm,
    decision_to_domain,
    decision_to_orm,
    diagnosis_to_domain,
    diagnosis_to_orm,
    execution_to_domain,
    execution_to_orm,
    outcome_to_domain,
    outcome_to_orm,
    payment_event_to_domain,
    payment_event_to_orm,
    payment_to_domain,
    payment_to_orm,
    policy_decision_to_domain,
    policy_decision_to_orm,
    recovery_action_to_domain,
    recovery_action_to_orm,
    recovery_case_to_domain,
    recovery_case_to_orm,
)


def test_customer_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    cust_id = str(uuid.uuid4())
    cust = Customer(
        customer_id=cust_id,
        external_reference="ext_ref_1",
        created_at=now,
        updated_at=now,
        historical_payment_count=2,
    )
    orm = customer_to_orm(cust)
    assert str(orm.customer_id) == cust_id
    assert orm.historical_payment_count == 2

    restored = customer_to_domain(orm)
    assert restored == cust


def test_payment_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    pay_id = str(uuid.uuid4())
    cust_id = str(uuid.uuid4())
    pay = Payment(
        payment_id=pay_id,
        customer_id=cust_id,
        provider="razorpay",
        amount=5000,  # paise
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
        failed_at=now,
    )
    orm = payment_to_orm(pay)
    assert str(orm.payment_id) == pay_id
    assert isinstance(orm.amount, int)
    assert orm.amount == 5000

    restored = payment_to_domain(orm)
    assert restored == pay


def test_payment_event_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    evt_id = str(uuid.uuid4())
    pay_id = str(uuid.uuid4())
    evt = PaymentEvent(
        event_id=evt_id,
        provider="razorpay",
        event_type="payment.failed",
        payment_id=pay_id,
        amount=5000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        event_timestamp=now,
        received_at=now,
    )
    orm = payment_event_to_orm(evt)
    assert str(orm.event_id) == evt_id

    restored = payment_event_to_domain(orm)
    assert restored == evt


def test_recovery_case_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    case_id = str(uuid.uuid4())
    pay_id = str(uuid.uuid4())
    cust_id = str(uuid.uuid4())
    case = RecoveryCase(
        case_id=case_id,
        payment_id=pay_id,
        customer_id=cust_id,
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
    )
    orm = recovery_case_to_orm(case)
    assert str(orm.case_id) == case_id

    restored = recovery_case_to_domain(orm)
    assert restored == case


def test_recovery_action_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    act_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    act = RecoveryAction(
        action_id=act_id,
        case_id=case_id,
        action_type=RecoveryActionType.RETRY,
        status=RecoveryActionStatus.CANDIDATE,
        created_at=now,
        updated_at=now,
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        parameters={"delay": 300},
    )
    orm = recovery_action_to_orm(act)
    assert str(orm.action_id) == act_id
    assert orm.execution_mode == "RAZORPAY_TEST_MODE"

    restored = recovery_action_to_domain(orm)
    assert restored == act


def test_diagnosis_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    diag_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    diag = Diagnosis(
        diagnosis_id=diag_id,
        case_id=case_id,
        category=FailureCategory.TRANSIENT,
        confidence=0.9,
        evidence=("timeout", "retryable"),
        model_name="diag_v1",
        model_version="1.0",
        created_at=now,
    )
    orm = diagnosis_to_orm(diag)
    assert str(orm.diagnosis_id) == diag_id
    assert orm.evidence == ["timeout", "retryable"]

    restored = diagnosis_to_domain(orm)
    assert restored == diag


def test_action_evaluation_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    eval_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    eval_obj = ActionEvaluation(
        evaluation_id=eval_id,
        case_id=case_id,
        action_type=RecoveryActionType.RETRY,
        success_probability=0.8,
        recoverable_amount=5000,
        action_cost=100,
        expected_recovery_value=3900,
        model_name="eval_v1",
        model_version="1.0",
        created_at=now,
    )
    orm = action_evaluation_to_orm(eval_obj)
    assert str(orm.evaluation_id) == eval_id

    restored = action_evaluation_to_domain(orm)
    assert restored == eval_obj


def test_decision_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    dec_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    dec = Decision(
        decision_id=dec_id,
        case_id=case_id,
        recommended_action=RecoveryActionType.RETRY,
        confidence=0.85,
        expected_recovery_value=3900,
        reason="High expected value",
        model_name="dec_v1",
        model_version="1.0",
        created_at=now,
    )
    orm = decision_to_orm(dec)
    assert str(orm.decision_id) == dec_id

    restored = decision_to_domain(orm)
    assert restored == dec


def test_policy_decision_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    pdec_id = str(uuid.uuid4())
    dec_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    pdec = PolicyDecision(
        policy_decision_id=pdec_id,
        decision_id=dec_id,
        case_id=case_id,
        result=PolicyDecisionResult.ALLOW,
        reason="Within policy bounds",
        policy_version="1.0",
        created_at=now,
    )
    orm = policy_decision_to_orm(pdec)
    assert str(orm.policy_decision_id) == pdec_id

    restored = policy_decision_to_domain(orm)
    assert restored == pdec


def test_execution_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    exec_id = str(uuid.uuid4())
    act_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    ex = Execution(
        execution_id=exec_id,
        action_id=act_id,
        case_id=case_id,
        execution_type="standard_retry",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        status=ExecutionStatus.PENDING,
        started_at=now,
    )
    orm = execution_to_orm(ex, idempotency_key="idempotency_key_100")
    assert str(orm.execution_id) == exec_id
    assert orm.idempotency_key == "idempotency_key_100"

    restored = execution_to_domain(orm)
    assert restored == ex


def test_outcome_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    out_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    out = Outcome(
        outcome_id=out_id,
        case_id=case_id,
        execution_id=exec_id,
        type=OutcomeType.RECOVERED,
        amount_recovered=5000,
        observed_at=now,
    )
    orm = outcome_to_orm(out)
    assert str(orm.outcome_id) == out_id

    restored = outcome_to_domain(orm)
    assert restored == out


def test_audit_event_mapping_roundtrip() -> None:
    now = datetime.now(UTC)
    aud_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    aud = AuditEvent(
        audit_event_id=aud_id,
        case_id=case_id,
        event_type="CASE_CREATED",
        actor=AuditActor.SYSTEM,
        timestamp=now,
        payload={"key": "val"},
    )
    orm = audit_event_to_orm(aud)
    assert str(orm.audit_event_id) == aud_id

    restored = audit_event_to_domain(orm)
    assert restored == aud
