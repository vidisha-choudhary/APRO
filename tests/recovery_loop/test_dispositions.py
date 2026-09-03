"""Unit tests for DispositionResolver in Phase 13."""

from datetime import UTC, datetime

from apro.domain.enums import (
    OutcomeType,
    PaymentStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Outcome, Payment, RecoveryCase
from apro.recovery_loop.dispositions import DispositionResolver
from apro.recovery_loop.enums import (
    LoopTerminationReason,
    RecoveryLoopDisposition,
)
from apro.recovery_loop.guards import LoopSafetyGuard
from apro.recovery_loop.models import ActionHistoryRecord


def _sample_payment(status: PaymentStatus = PaymentStatus.FAILED) -> Payment:
    now = datetime.now(UTC)
    return Payment(
        payment_id="pay_disp_01",
        customer_id="cust_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=status,
        created_at=now,
        updated_at=now,
    )


def _sample_case(
    status: RecoveryCaseStatus = RecoveryCaseStatus.OBSERVING,
) -> RecoveryCase:
    now = datetime.now(UTC)
    return RecoveryCase(
        case_id="case_disp_01",
        payment_id="pay_disp_01",
        customer_id="cust_01",
        status=status,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )


def test_recovered_outcome_yields_complete() -> None:
    resolver = DispositionResolver()
    now = datetime.now(UTC)
    outcome = Outcome(
        outcome_id="out_01",
        case_id="case_disp_01",
        execution_id="exec_01",
        type=OutcomeType.RECOVERED,
        amount_recovered=50000,
        observed_at=now,
    )
    disp, reason = resolver.resolve(
        outcome=outcome,
        case=_sample_case(),
        payment=_sample_payment(),
        history=[],
        cycle_number=1,
    )
    assert disp == RecoveryLoopDisposition.COMPLETE
    assert reason == LoopTerminationReason.RECOVERY_CONFIRMED


def test_pending_outcome_yields_wait_for_outcome() -> None:
    resolver = DispositionResolver()
    now = datetime.now(UTC)
    outcome = Outcome(
        outcome_id="out_02",
        case_id="case_disp_01",
        execution_id="exec_02",
        type=OutcomeType.PENDING,
        amount_recovered=0,
        observed_at=now,
    )
    disp, reason = resolver.resolve(
        outcome=outcome,
        case=_sample_case(),
        payment=_sample_payment(),
        history=[],
        cycle_number=1,
    )
    assert disp == RecoveryLoopDisposition.WAIT_FOR_OUTCOME
    assert reason is None


def test_failed_outcome_under_limits_yields_re_evaluate() -> None:
    resolver = DispositionResolver()
    now = datetime.now(UTC)
    outcome = Outcome(
        outcome_id="out_03",
        case_id="case_disp_01",
        execution_id="exec_03",
        type=OutcomeType.FAILED,
        amount_recovered=0,
        observed_at=now,
    )
    disp, reason = resolver.resolve(
        outcome=outcome,
        case=_sample_case(),
        payment=_sample_payment(),
        history=[],
        cycle_number=1,
    )
    assert disp == RecoveryLoopDisposition.RE_EVALUATE
    assert reason is None


def test_failed_outcome_exceeding_max_attempts_yields_stop() -> None:
    guard = LoopSafetyGuard(max_attempts=2)
    resolver = DispositionResolver(safety_guard=guard)
    now = datetime.now(UTC)
    outcome = Outcome(
        outcome_id="out_04",
        case_id="case_disp_01",
        execution_id="exec_04",
        type=OutcomeType.FAILED,
        amount_recovered=0,
        observed_at=now,
    )
    history = [
        ActionHistoryRecord(
            action_id="act_01",
            action_type=RecoveryActionType.RETRY,
            execution_id="exec_01",
            observed_at=now,
            attempt_order=1,
        ),
        ActionHistoryRecord(
            action_id="act_02",
            action_type=RecoveryActionType.ALTERNATE_RECOVERY,
            execution_id="exec_02",
            observed_at=now,
            attempt_order=2,
        ),
    ]
    disp, reason = resolver.resolve(
        outcome=outcome,
        case=_sample_case(),
        payment=_sample_payment(),
        history=history,
        cycle_number=2,
    )
    assert disp == RecoveryLoopDisposition.STOP
    assert reason == LoopTerminationReason.ATTEMPT_LIMIT_EXCEEDED
