"""Unit tests for execution validation and precondition checking."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

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
    ExecutionStateError,
    ExecutionValidationError,
)
from apro.execution.executors.outreach import SimulationOutreachExecutor
from apro.execution.executors.retry import SimulationRetryExecutor
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.execution.registry import ExecutorRegistry
from apro.execution.validation import (
    build_approved_execution_request,
    validate_execution_preconditions,
    validate_parameter_secrets,
    validate_policy_authorization,
)
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import PolicyDecision
from apro.recovery_prediction.enums import RecoveryAction as PredictRecoveryAction


def _make_fixture(
    outcome: PolicyOutcome = PolicyOutcome.ALLOW,
    effective_action: PredictRecoveryAction | None = PredictRecoveryAction.RETRY,
    approval_ref: str | None = None,
    payment_status: PaymentStatus = PaymentStatus.FAILED,
    action_status: RecoveryActionStatus = RecoveryActionStatus.APPROVED,
    case_status: RecoveryCaseStatus = RecoveryCaseStatus.ACTION_APPROVED,
) -> tuple[PolicyDecision, RecoveryAction, RecoveryCase, Payment]:
    now = datetime.now(UTC)
    reason = (
        PolicyReasonCode.POLICY_ALLOWED
        if outcome == PolicyOutcome.ALLOW
        else PolicyReasonCode.MAX_RETRIES_REACHED
    )
    pol = PolicyDecision(
        policy_decision_id="pol_dec_001",
        case_id="case_001",
        payment_id="pay_001",
        decision_id="dec_001",
        requested_action=effective_action,
        policy_outcome=outcome,
        effective_action=effective_action,
        reason_code=reason,
        reason_detail="Policy evaluation",
        approval_reference=approval_ref,
        idempotency_key="idem_case_001_RETRY_1",
        payment_state_observed=payment_status,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        created_at=now,
    )
    act = RecoveryAction(
        action_id="act_001",
        case_id="case_001",
        action_type=RecoveryActionType.RETRY,
        status=action_status,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_001",
        payment_id="pay_001",
        customer_id="cust_001",
        status=case_status,
        opened_at=now,
        updated_at=now,
    )
    pay = Payment(
        payment_id="pay_001",
        customer_id="cust_001",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=payment_status,
        created_at=now,
        updated_at=now,
    )
    return pol, act, case, pay


def test_validate_policy_authorization_allow_success() -> None:
    """Verify authorized ALLOW policy passes validation."""
    pol, act, case, pay = _make_fixture()
    validate_policy_authorization(pol, act, case, pay)


def test_validate_policy_authorization_block_rejected() -> None:
    """Verify BLOCK outcome raises ExecutionAuthorizationError."""
    pol, act, case, pay = _make_fixture(
        outcome=PolicyOutcome.BLOCK, effective_action=None
    )
    with pytest.raises(ExecutionAuthorizationError, match="BLOCK"):
        validate_policy_authorization(pol, act, case, pay)


def test_validate_policy_authorization_approval_without_ref_rejected() -> None:
    """Verify unapproved human approval raises ExecutionAuthorizationError."""
    pol, act, case, pay = _make_fixture(
        outcome=PolicyOutcome.REQUIRE_HUMAN_APPROVAL,
        approval_ref=None,
    )
    with pytest.raises(ExecutionAuthorizationError, match="requires human approval"):
        validate_policy_authorization(pol, act, case, pay)


def test_validate_policy_authorization_action_mismatch_rejected() -> None:
    """Verify action mismatch raises ExecutionValidationError."""
    pol, act, case, pay = _make_fixture(effective_action=PredictRecoveryAction.OUTREACH)
    with pytest.raises(ExecutionValidationError, match="Action mismatch"):
        validate_policy_authorization(pol, act, case, pay)


def test_validate_policy_authorization_case_mismatch_rejected() -> None:
    """Verify case_id mismatch raises ExecutionValidationError."""
    pol, act, case, pay = _make_fixture()
    case_bad = case.model_copy(update={"case_id": "case_DIFFERENT"})
    with pytest.raises(ExecutionValidationError, match="Case mismatch"):
        validate_policy_authorization(pol, act, case_bad, pay)


def test_validate_execution_preconditions_captured_payment_rejected() -> None:
    """Verify CAPTURED payment status raises ExecutionStateError."""
    pol, act, case, pay = _make_fixture(payment_status=PaymentStatus.CAPTURED)
    with pytest.raises(ExecutionStateError, match="CAPTURED"):
        validate_execution_preconditions(act, case, pay, ExecutionMode.SIMULATION)


def test_validate_execution_preconditions_terminal_action_rejected() -> None:
    """Verify terminal action raises ExecutionStateError."""
    pol, act, case, pay = _make_fixture(action_status=RecoveryActionStatus.COMPLETED)
    with pytest.raises(ExecutionStateError, match="terminal state"):
        validate_execution_preconditions(act, case, pay, ExecutionMode.SIMULATION)


def test_validate_parameter_secrets_forbidden_keys() -> None:
    """Verify credential and secret keys in parameters raise error."""
    with pytest.raises(ExecutionValidationError, match="Forbidden credential/secret"):
        validate_parameter_secrets({"api_key": "rzp_test_12345"})

    with pytest.raises(ExecutionValidationError, match="Forbidden credential/secret"):
        validate_parameter_secrets({"client_secret": "my_secret_key"})


def test_build_approved_execution_request() -> None:
    """Verify build_approved_execution_request builds expected model."""
    pol, act, case, pay = _make_fixture()
    req = build_approved_execution_request(
        policy_decision=pol,
        action=act,
        case=case,
        execution_mode=ExecutionMode.SIMULATION,
        parameters={"retry_delay_seconds": 30},
    )
    assert req.case_id == "case_001"
    assert req.action_id == "act_001"
    assert req.action_type == RecoveryActionType.RETRY
    assert req.idempotency_key == "idem_case_001_RETRY_1"
    assert req.parameters["retry_delay_seconds"] == 30


@pytest.mark.asyncio
async def test_invalid_parameters_rejected_before_dispatch_and_no_state_mutations() -> (
    None
):
    """Verify invalid executor parameters fail before dispatch without state changes."""
    pol, act, case, pay = _make_fixture()

    mock_executor = MagicMock(spec=SimulationRetryExecutor)
    mock_executor.action_type = RecoveryActionType.RETRY
    mock_executor.supported_modes = {ExecutionMode.SIMULATION}
    mock_executor.validate.side_effect = ExecutionValidationError("Invalid delay")
    mock_executor.execute = AsyncMock()

    registry = ExecutorRegistry()
    registry.register(mock_executor)
    orchestrator = ExecutionOrchestrator(registry=registry)

    with pytest.raises(ExecutionValidationError, match="Invalid delay"):
        await orchestrator.execute(
            policy_decision=pol,
            recovery_action=act,
            recovery_case=case,
            payment=pay,
            execution_mode=ExecutionMode.SIMULATION,
            parameters={"retry_delay_seconds": -10},
        )

    # 1. Assert executor was NEVER invoked
    assert mock_executor.execute.call_count == 0

    # 2. Assert entity states were NOT prematurely mutated
    assert act.status == RecoveryActionStatus.APPROVED
    assert case.status == RecoveryCaseStatus.ACTION_APPROVED


@pytest.mark.asyncio
async def test_invalid_outreach_channel_rejected_before_dispatch() -> None:
    """Verify unsupported outreach channel fails validation before dispatch."""
    pol, act, case, pay = _make_fixture(effective_action=PredictRecoveryAction.OUTREACH)
    act_out = act.model_copy(update={"action_type": RecoveryActionType.OUTREACH})

    mock_executor = MagicMock(spec=SimulationOutreachExecutor)
    mock_executor.action_type = RecoveryActionType.OUTREACH
    mock_executor.supported_modes = {ExecutionMode.SIMULATION}
    mock_executor.validate.side_effect = ExecutionValidationError(
        "Unsupported outreach channel"
    )
    mock_executor.execute = AsyncMock()

    registry = ExecutorRegistry()
    registry.register(mock_executor)
    orchestrator = ExecutionOrchestrator(registry=registry)

    with pytest.raises(ExecutionValidationError, match="Unsupported outreach channel"):
        await orchestrator.execute(
            policy_decision=pol,
            recovery_action=act_out,
            recovery_case=case,
            payment=pay,
            execution_mode=ExecutionMode.SIMULATION,
            parameters={"channel": "smoke_signals"},
        )

    assert mock_executor.execute.call_count == 0
