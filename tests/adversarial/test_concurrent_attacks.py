"""Tests for Scenario 4: Concurrency, Preemption, and Payment Capture Racing."""

from datetime import UTC, datetime

import pytest

from apro.adversarial.enums import AttackDisposition
from apro.adversarial.executor import AdversarialAttackExecutor
from apro.adversarial.generators import generate_capture_race_cases
from apro.domain.enums import PaymentStatus
from apro.domain.models import Payment
from apro.policy.enums import PolicyReasonCode
from apro.policy.state_guard import StateGuard
from apro.recovery_prediction.enums import RecoveryAction


@pytest.mark.asyncio
async def test_scenario_4_capture_race_cases(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """Scenario 4: StateGuard rejects the stale/unsafe execution attempt before provider dispatch."""
    cases = generate_capture_race_cases(seed=1701, count=5)

    for case in cases:
        result = await adversarial_executor.execute_case(case)
        assert result.passed is True
        assert result.disposition == AttackDisposition.BLOCKED
        assert (
            "StateGuard rejects the stale/unsafe execution attempt"
            in result.observed_property
        )


def test_scenario_4_stateguard_direct_recheck_captured() -> None:
    """Direct StateGuard check rejects retry when payment is already captured."""
    now = datetime.now(UTC)
    payment = Payment(
        payment_id="pay_captured_race_001",
        customer_id="cust_001",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.CAPTURED,
        created_at=now,
        updated_at=now,
    )

    allowed, reason, detail = StateGuard.recheck(payment, RecoveryAction.RETRY)

    assert allowed is False
    assert reason == PolicyReasonCode.PAYMENT_ALREADY_RECOVERED
    assert detail is not None
    assert "already recovered" in detail.lower() or "captured" in detail.lower()


@pytest.mark.asyncio
async def test_scenario_4_real_concurrent_race_synchronization(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """Scenario 4: Prove concurrent payment capture preemption prevents provider dispatch."""
    case = generate_capture_race_cases(seed=42, count=1)[0]
    result = await adversarial_executor.execute_case(case)

    assert result.passed is True
    assert result.disposition == AttackDisposition.BLOCKED
    assert result.sanitized_evidence.get("rejected_cleanly") is True
    assert result.sanitized_evidence.get("provider_dispatches") == 0
    assert result.sanitized_evidence.get("final_payment_status") == "CAPTURED"
