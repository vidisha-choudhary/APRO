"""Tests for Scenario 5: State Machine Boundary and Terminal Reversal Attacks."""

from datetime import UTC, datetime

import pytest

from apro.adversarial.enums import AttackDisposition
from apro.adversarial.executor import AdversarialAttackExecutor
from apro.adversarial.generators import generate_illegal_state_cases
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.exceptions import InvalidStateTransitionError
from apro.domain.models import Payment, RecoveryCase
from apro.domain.state_machines import transition_recovery_case


@pytest.mark.asyncio
async def test_scenario_5_illegal_state_cases(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """Scenario 5: Illegal state transitions and terminal reversals are strictly rejected."""
    cases = generate_illegal_state_cases(seed=1701, count=5)

    for case in cases:
        result = await adversarial_executor.execute_case(case)
        assert result.passed is True
        assert result.disposition == AttackDisposition.REJECTED


def test_scenario_5_direct_terminal_state_reversal_rejected() -> None:
    """Direct state machine transition from RECOVERED to EXECUTING raises InvalidStateTransitionError."""
    now = datetime.now(UTC)
    case_obj = RecoveryCase(
        case_id="case_term_001",
        payment_id="pay_term_001",
        customer_id="cust_term_001",
        status=RecoveryCaseStatus.RECOVERED,
        opened_at=now,
        updated_at=now,
    )
    payment = Payment(
        payment_id="pay_term_001",
        customer_id="cust_term_001",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(InvalidStateTransitionError):
        transition_recovery_case(case_obj, payment, RecoveryCaseStatus.EXECUTING)
