"""Tests proving stale policy decisions cannot authorize later different
actions in Phase 13.
"""

from datetime import UTC, datetime

import pytest

from apro.domain.enums import (
    ExecutionMode,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Payment, RecoveryAction, RecoveryCase
from apro.execution.exceptions import (
    ExecutionAuthorizationError,
    ExecutionValidationError,
)
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.policy.enums import (
    PolicyOutcome,
    PolicyReasonCode,
)
from apro.policy.models import PolicyDecision
from apro.recovery_prediction.enums import (
    RecoveryAction as PredictorAction,
)


@pytest.mark.asyncio
async def test_stale_policy_decision_rejected_for_changed_action() -> None:
    """Guardrail 6: PolicyDecision 1 (ALLOW for RETRY) must NOT authorize
    Action 2 (ALTERNATE_RECOVERY).

    Phase 11 Execution Orchestrator validates that the policy decision's
    requested/effective action strictly matches the recovery action to be
    executed.
    """
    orchestrator = ExecutionOrchestrator()
    now = datetime.now(UTC)

    payment = Payment(
        payment_id="pay_stale_01",
        customer_id="cust_stale_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_stale_01",
        payment_id="pay_stale_01",
        customer_id="cust_stale_01",
        status=RecoveryCaseStatus.ACTION_APPROVED,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )

    # Policy Decision 1 authorized RETRY (Action 1)
    stale_policy_decision_1 = PolicyDecision(
        policy_decision_id="pol_dec_cycle_1",
        case_id="case_stale_01",
        payment_id="pay_stale_01",
        decision_id="dec_cycle_1",
        requested_action=PredictorAction.RETRY,
        policy_outcome=PolicyOutcome.ALLOW,
        effective_action=PredictorAction.RETRY,
        reason_code=PolicyReasonCode.POLICY_ALLOWED,
        reason_detail="Rule allow",
        payment_state_observed=PaymentStatus.FAILED,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        created_at=now,
    )

    # Action 2 is ALTERNATE_RECOVERY (produced in Cycle 2)
    action_2 = RecoveryAction(
        action_id="act_stale_02",
        case_id="case_stale_01",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
        execution_mode=ExecutionMode.SIMULATION,
        parameters={"amount": 50000},
    )

    # Attempting to execute Action 2 using stale PolicyDecision 1
    # must raise ExecutionValidationError
    with pytest.raises(
        (ExecutionAuthorizationError, ExecutionValidationError)
    ) as exc_info:
        await orchestrator.execute(
            policy_decision=stale_policy_decision_1,
            recovery_action=action_2,
            recovery_case=case,
            payment=payment,
            execution_mode=ExecutionMode.SIMULATION,
            current_time=now,
            parameters={"amount": 50000},
        )

    assert (
        "mismatch" in str(exc_info.value).lower()
        or "action" in str(exc_info.value).lower()
    )
