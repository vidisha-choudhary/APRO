"""Integration tests for PolicyDecision -> Orchestrator -> Razorpay Adapter."""

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
from apro.domain.models import Payment, RecoveryAction, RecoveryCase
from apro.execution.exceptions import (
    ExecutionAuthorizationError,
    ExecutionStateError,
)
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.execution.registry import ExecutorRegistry
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import PolicyDecision
from apro.providers.razorpay.adapter import (
    RazorpayTestModeOutreachExecutor,
    RazorpayTestModePaymentLinkExecutor,
)
from apro.providers.razorpay.client import RazorpayTestModeClient
from apro.providers.razorpay.config import RazorpayTestModeConfig
from apro.providers.razorpay.stub import DeterministicRazorpayStub
from apro.recovery_prediction.enums import RecoveryAction as PredAct


def _make_fixture(
    action_type: RecoveryActionType = RecoveryActionType.ALTERNATE_RECOVERY,
    pred_action: PredAct = PredAct.PAYMENT_LINK,
    policy_outcome: PolicyOutcome = PolicyOutcome.ALLOW,
    payment_status: PaymentStatus = PaymentStatus.FAILED,
    approval_ref: str | None = None,
) -> tuple[PolicyDecision, RecoveryAction, RecoveryCase, Payment]:
    now = datetime.now(UTC)
    pay = Payment(
        payment_id="pay_integ_01",
        customer_id="cust_integ_01",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=payment_status,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_integ_01",
        payment_id="pay_integ_01",
        customer_id="cust_integ_01",
        status=RecoveryCaseStatus.ACTION_APPROVED,
        opened_at=now,
        updated_at=now,
    )
    act = RecoveryAction(
        action_id="act_integ_01",
        case_id="case_integ_01",
        action_type=action_type,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
        parameters={"amount": 50000, "customer_name": "Test User"},
    )
    pol = PolicyDecision(
        policy_decision_id="pol_integ_01",
        case_id="case_integ_01",
        payment_id="pay_integ_01",
        decision_id="dec_integ_01",
        requested_action=pred_action if policy_outcome != PolicyOutcome.BLOCK else None,
        policy_outcome=policy_outcome,
        effective_action=pred_action if policy_outcome == PolicyOutcome.ALLOW else None,
        reason_code=PolicyReasonCode.POLICY_ALLOWED
        if policy_outcome == PolicyOutcome.ALLOW
        else PolicyReasonCode.PAYMENT_ALREADY_RECOVERED,
        reason_detail="Policy authorized"
        if policy_outcome == PolicyOutcome.ALLOW
        else "Blocked",
        idempotency_key="idem_integ_01",
        approval_reference=approval_ref,
        payment_state_observed=payment_status,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="out-v1",
        created_at=now,
    )
    return pol, act, case, pay


@pytest.fixture
def integ_registry() -> tuple[ExecutorRegistry, DeterministicRazorpayStub]:
    stub = DeterministicRazorpayStub()
    cfg = RazorpayTestModeConfig(
        key_id="rzp_test_mock_12345",
        key_secret="mock_secret_12345",
    )
    client = RazorpayTestModeClient(config=cfg, transport=stub)
    registry = ExecutorRegistry()
    registry.register(RazorpayTestModePaymentLinkExecutor(client=client))
    registry.register(RazorpayTestModeOutreachExecutor(client=client))
    return registry, stub


@pytest.mark.asyncio
async def test_full_chain_authorized_payment_link_dispatch(
    integ_registry: tuple[ExecutorRegistry, DeterministicRazorpayStub],
) -> None:
    """Verify Policy -> Orchestrator -> Razorpay Adapter returns SUCCEEDED."""
    registry, stub = integ_registry
    orchestrator = ExecutionOrchestrator(registry=registry)
    pol, act, case, pay = _make_fixture()

    result = await orchestrator.execute(
        pol, act, case, pay, ExecutionMode.RAZORPAY_TEST_MODE
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.provider_reference is not None
    assert "short_url" in result.metadata
    assert len(stub.recorded_requests) == 1


@pytest.mark.asyncio
async def test_block_decision_cannot_reach_razorpay_adapter(
    integ_registry: tuple[ExecutorRegistry, DeterministicRazorpayStub],
) -> None:
    """Verify PolicyOutcome.BLOCK raises ExecutionAuthorizationError (0 calls)."""
    registry, stub = integ_registry
    orchestrator = ExecutionOrchestrator(registry=registry)
    pol, act, case, pay = _make_fixture(
        policy_outcome=PolicyOutcome.BLOCK,
        payment_status=PaymentStatus.CAPTURED,
    )

    with pytest.raises(ExecutionAuthorizationError):
        await orchestrator.execute(
            pol, act, case, pay, ExecutionMode.RAZORPAY_TEST_MODE
        )

    assert len(stub.recorded_requests) == 0


@pytest.mark.asyncio
async def test_captured_payment_fails_stateguard_before_dispatch(
    integ_registry: tuple[ExecutorRegistry, DeterministicRazorpayStub],
) -> None:
    """Verify captured payment dynamically caught by StateGuard (0 calls)."""
    registry, stub = integ_registry
    orchestrator = ExecutionOrchestrator(registry=registry)
    pol, act, case, pay = _make_fixture()

    def capture_now() -> None:
        pay.status = PaymentStatus.CAPTURED

    orchestrator._pre_gate_hook = capture_now

    with pytest.raises(ExecutionStateError):
        await orchestrator.execute(
            pol, act, case, pay, ExecutionMode.RAZORPAY_TEST_MODE
        )

    assert len(stub.recorded_requests) == 0
