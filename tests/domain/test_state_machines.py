"""Unit tests for domain state machine transitions and core invariants."""

from datetime import UTC, datetime

import pytest

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.exceptions import (
    CapturedPaymentRecoveryError,
    InvalidStateTransitionError,
)
from apro.domain.models import Execution, Payment, RecoveryAction, RecoveryCase
from apro.domain.state_machines import (
    transition_execution,
    transition_payment,
    transition_recovery_action,
    transition_recovery_case,
    validate_payment_recovery_eligibility,
)


@pytest.fixture
def sample_payment() -> Payment:
    now = datetime.now(UTC)
    return Payment(
        payment_id="pay_failed_100",
        customer_id="cust_100",
        provider="razorpay",
        amount=2500,
        currency="INR",
        method="upi",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_captured_payment() -> Payment:
    now = datetime.now(UTC)
    return Payment(
        payment_id="pay_captured_200",
        customer_id="cust_200",
        provider="razorpay",
        amount=2500,
        currency="INR",
        method="upi",
        status=PaymentStatus.CAPTURED,
        created_at=now,
        updated_at=now,
        captured_at=now,
    )


@pytest.fixture
def sample_recovery_case(sample_payment: Payment) -> RecoveryCase:
    now = datetime.now(UTC)
    return RecoveryCase(
        case_id="case_100",
        payment_id=sample_payment.payment_id,
        customer_id=sample_payment.customer_id,
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
    )


# ==============================================================================
# Payment State Machine Tests
# ==============================================================================


def test_payment_valid_transitions() -> None:
    now = datetime.now(UTC)
    pay = Payment(
        payment_id="pay_1",
        customer_id="cust_1",
        provider="razorpay",
        amount=1000,
        currency="INR",
        method="card",
        status=PaymentStatus.CREATED,
        created_at=now,
        updated_at=now,
    )

    pay_auth = transition_payment(pay, PaymentStatus.AUTHORIZED)
    assert pay_auth.status == PaymentStatus.AUTHORIZED

    pay_cap = transition_payment(pay_auth, PaymentStatus.CAPTURED)
    assert pay_cap.status == PaymentStatus.CAPTURED
    assert pay_cap.captured_at is not None


def test_payment_failed_to_pending_to_captured() -> None:
    now = datetime.now(UTC)
    pay_failed = Payment(
        payment_id="pay_2",
        customer_id="cust_1",
        provider="razorpay",
        amount=1000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )

    pay_pending = transition_payment(pay_failed, PaymentStatus.PENDING)
    assert pay_pending.status == PaymentStatus.PENDING

    pay_captured = transition_payment(pay_pending, PaymentStatus.CAPTURED)
    assert pay_captured.status == PaymentStatus.CAPTURED


def test_payment_captured_terminal_state_lock(
    sample_captured_payment: Payment,
) -> None:
    with pytest.raises(CapturedPaymentRecoveryError):
        transition_payment(sample_captured_payment, PaymentStatus.FAILED)


def test_payment_invalid_transition(sample_payment: Payment) -> None:
    # FAILED cannot transition back to CREATED
    with pytest.raises(InvalidStateTransitionError):
        transition_payment(sample_payment, PaymentStatus.CREATED)


# ==============================================================================
# RecoveryCase State Machine Tests
# ==============================================================================


def test_recovery_case_primary_lifecycle(
    sample_recovery_case: RecoveryCase, sample_payment: Payment
) -> None:
    c1 = transition_recovery_case(
        sample_recovery_case, sample_payment, RecoveryCaseStatus.DIAGNOSING
    )
    assert c1.status == RecoveryCaseStatus.DIAGNOSING

    c2 = transition_recovery_case(c1, sample_payment, RecoveryCaseStatus.EVALUATING)
    assert c2.status == RecoveryCaseStatus.EVALUATING

    c3 = transition_recovery_case(
        c2, sample_payment, RecoveryCaseStatus.DECISION_PENDING
    )
    assert c3.status == RecoveryCaseStatus.DECISION_PENDING

    c4 = transition_recovery_case(c3, sample_payment, RecoveryCaseStatus.POLICY_CHECK)
    assert c4.status == RecoveryCaseStatus.POLICY_CHECK

    c5 = transition_recovery_case(
        c4, sample_payment, RecoveryCaseStatus.ACTION_APPROVED
    )
    assert c5.status == RecoveryCaseStatus.ACTION_APPROVED

    c6 = transition_recovery_case(c5, sample_payment, RecoveryCaseStatus.EXECUTING)
    assert c6.status == RecoveryCaseStatus.EXECUTING

    c7 = transition_recovery_case(c6, sample_payment, RecoveryCaseStatus.OBSERVING)
    assert c7.status == RecoveryCaseStatus.OBSERVING

    c8 = transition_recovery_case(c7, sample_payment, RecoveryCaseStatus.RECOVERED)
    assert c8.status == RecoveryCaseStatus.RECOVERED
    assert c8.closed_at is not None


def test_recovery_case_observation_failure_re_evaluation(
    sample_recovery_case: RecoveryCase, sample_payment: Payment
) -> None:
    # Advance to OBSERVING
    c = sample_recovery_case
    for st in [
        RecoveryCaseStatus.DIAGNOSING,
        RecoveryCaseStatus.EVALUATING,
        RecoveryCaseStatus.DECISION_PENDING,
        RecoveryCaseStatus.POLICY_CHECK,
        RecoveryCaseStatus.ACTION_APPROVED,
        RecoveryCaseStatus.EXECUTING,
        RecoveryCaseStatus.OBSERVING,
    ]:
        c = transition_recovery_case(c, sample_payment, st)

    # Observation reveals failed outcome -> re-evaluate
    c_re = transition_recovery_case(c, sample_payment, RecoveryCaseStatus.EVALUATING)
    assert c_re.status == RecoveryCaseStatus.EVALUATING


def test_recovery_case_direct_termination(
    sample_recovery_case: RecoveryCase, sample_payment: Payment
) -> None:
    c_stopped = transition_recovery_case(
        sample_recovery_case, sample_payment, RecoveryCaseStatus.STOPPED
    )
    assert c_stopped.status == RecoveryCaseStatus.STOPPED
    assert c_stopped.closed_at is not None

    c_escalated = transition_recovery_case(
        sample_recovery_case, sample_payment, RecoveryCaseStatus.ESCALATED
    )
    assert c_escalated.status == RecoveryCaseStatus.ESCALATED
    assert c_escalated.closed_at is not None


def test_recovery_case_terminal_states_lock(
    sample_recovery_case: RecoveryCase, sample_payment: Payment
) -> None:
    c_stopped = transition_recovery_case(
        sample_recovery_case, sample_payment, RecoveryCaseStatus.STOPPED
    )
    with pytest.raises(InvalidStateTransitionError):
        transition_recovery_case(
            c_stopped, sample_payment, RecoveryCaseStatus.EVALUATING
        )


def test_recovery_case_prohibited_backward_jump(
    sample_recovery_case: RecoveryCase, sample_payment: Payment
) -> None:
    c_exec = transition_recovery_case(
        sample_recovery_case, sample_payment, RecoveryCaseStatus.DIAGNOSING
    )
    with pytest.raises(InvalidStateTransitionError):
        transition_recovery_case(
            c_exec, sample_payment, RecoveryCaseStatus.ACTION_APPROVED
        )


# ==============================================================================
# Captured Payment Safety Invariant Tests
# ==============================================================================


def test_validate_payment_recovery_eligibility(
    sample_payment: Payment, sample_captured_payment: Payment
) -> None:
    # FAILED payment is eligible
    validate_payment_recovery_eligibility(sample_payment)

    # CAPTURED payment raises CapturedPaymentRecoveryError
    with pytest.raises(CapturedPaymentRecoveryError):
        validate_payment_recovery_eligibility(sample_captured_payment)


def test_captured_payment_blocks_recovery_execution_transitions(
    sample_recovery_case: RecoveryCase, sample_captured_payment: Payment
) -> None:
    # Attempting to transition RecoveryCase to ACTION_APPROVED when Payment is CAPTURED
    with pytest.raises(CapturedPaymentRecoveryError):
        transition_recovery_case(
            sample_recovery_case,
            sample_captured_payment,
            RecoveryCaseStatus.ACTION_APPROVED,
        )

    # Attempting to transition RecoveryCase to EXECUTING when Payment is CAPTURED
    with pytest.raises(CapturedPaymentRecoveryError):
        transition_recovery_case(
            sample_recovery_case,
            sample_captured_payment,
            RecoveryCaseStatus.EXECUTING,
        )


def test_captured_payment_allows_non_execution_transitions_without_side_effects(
    sample_recovery_case: RecoveryCase, sample_captured_payment: Payment
) -> None:
    # Per Architecture Lead Locked Decision 3:
    # transition remains deterministic without auto-mutating
    c_diag = transition_recovery_case(
        sample_recovery_case,
        sample_captured_payment,
        RecoveryCaseStatus.DIAGNOSING,
    )
    assert c_diag.status == RecoveryCaseStatus.DIAGNOSING

    c_stop = transition_recovery_case(
        c_diag, sample_captured_payment, RecoveryCaseStatus.STOPPED
    )
    assert c_stop.status == RecoveryCaseStatus.STOPPED


# ==============================================================================
# RecoveryAction State Machine Tests
# ==============================================================================


def test_recovery_action_valid_transitions() -> None:
    now = datetime.now(UTC)
    act = RecoveryAction(
        action_id="act_1",
        case_id="case_1",
        action_type=RecoveryActionType.RETRY,
        status=RecoveryActionStatus.CANDIDATE,
        created_at=now,
        updated_at=now,
    )

    a1 = transition_recovery_action(act, RecoveryActionStatus.RECOMMENDED)
    assert a1.status == RecoveryActionStatus.RECOMMENDED

    a2 = transition_recovery_action(a1, RecoveryActionStatus.APPROVED)
    assert a2.status == RecoveryActionStatus.APPROVED

    a3 = transition_recovery_action(a2, RecoveryActionStatus.EXECUTING)
    assert a3.status == RecoveryActionStatus.EXECUTING

    a4 = transition_recovery_action(a3, RecoveryActionStatus.COMPLETED)
    assert a4.status == RecoveryActionStatus.COMPLETED


def test_recovery_action_terminal_state_lock() -> None:
    now = datetime.now(UTC)
    act = RecoveryAction(
        action_id="act_1",
        case_id="case_1",
        action_type=RecoveryActionType.RETRY,
        status=RecoveryActionStatus.COMPLETED,
        created_at=now,
        updated_at=now,
    )
    with pytest.raises(InvalidStateTransitionError):
        transition_recovery_action(act, RecoveryActionStatus.EXECUTING)


# ==============================================================================
# Execution State Machine Tests
# ==============================================================================


def test_execution_valid_transitions() -> None:
    now = datetime.now(UTC)
    ex = Execution(
        execution_id="exec_1",
        action_id="act_1",
        case_id="case_1",
        execution_type="standard_retry",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        status=ExecutionStatus.PENDING,
        started_at=now,
    )

    ex_run = transition_execution(ex, ExecutionStatus.RUNNING)
    assert ex_run.status == ExecutionStatus.RUNNING

    ex_succ = transition_execution(ex_run, ExecutionStatus.SUCCEEDED)
    assert ex_succ.status == ExecutionStatus.SUCCEEDED
    assert ex_succ.completed_at is not None


def test_execution_timeout_unknown_path() -> None:
    now = datetime.now(UTC)
    ex = Execution(
        execution_id="exec_1",
        action_id="act_1",
        case_id="case_1",
        execution_type="standard_retry",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        status=ExecutionStatus.RUNNING,
        started_at=now,
    )

    ex_unk = transition_execution(ex, ExecutionStatus.UNKNOWN)
    assert ex_unk.status == ExecutionStatus.UNKNOWN
    assert ex_unk.completed_at is not None


def test_execution_terminal_state_lock() -> None:
    now = datetime.now(UTC)
    ex = Execution(
        execution_id="exec_1",
        action_id="act_1",
        case_id="case_1",
        execution_type="standard_retry",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        status=ExecutionStatus.SUCCEEDED,
        started_at=now,
        completed_at=now,
    )
    with pytest.raises(InvalidStateTransitionError):
        transition_execution(ex, ExecutionStatus.RUNNING)
