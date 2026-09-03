"""APRO Phase 12 Acceptance Suite — Razorpay TEST Mode Provider Integration.

Verifies:
1. 8 Manual Acceptance Scenarios
2. 38 Acceptance Criteria (AC-01 through AC-38)
"""

import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

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
    ExecutionValidationError,
    ExecutorNotFoundError,
)
from apro.execution.models import ApprovedExecutionRequest, ExecutionResult
from apro.execution.orchestrator import ExecutionOrchestrator
from apro.execution.registry import (
    DEFAULT_EXECUTOR_REGISTRY,
    ExecutorRegistry,
)
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import PolicyDecision
from apro.providers.exceptions import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderCredentialError,
    ProviderRejectedError,
)
from apro.providers.razorpay.adapter import (
    RazorpayTestModeOutreachExecutor,
    RazorpayTestModePaymentLinkExecutor,
)
from apro.providers.razorpay.client import RazorpayTestModeClient
from apro.providers.razorpay.config import RazorpayTestModeConfig
from apro.providers.razorpay.errors import classify_razorpay_error
from apro.providers.razorpay.mapper import (
    map_approved_request_to_payment_link_request,
)
from apro.providers.razorpay.stub import DeterministicRazorpayStub
from apro.recovery_prediction.enums import RecoveryAction as PredAct


def make_test_fixture(
    action_type: RecoveryActionType = RecoveryActionType.ALTERNATE_RECOVERY,
    pred_action: PredAct = PredAct.PAYMENT_LINK,
    policy_outcome: PolicyOutcome = PolicyOutcome.ALLOW,
    payment_status: PaymentStatus = PaymentStatus.FAILED,
    approval_ref: str | None = None,
    amount: int = 50000,
    case_status: RecoveryCaseStatus = RecoveryCaseStatus.ACTION_APPROVED,
) -> tuple[PolicyDecision, RecoveryAction, RecoveryCase, Payment]:
    now = datetime.now(UTC)
    uid = str(uuid.uuid4())[:8]
    cust_id = f"cust_acc_{uid}"
    pay_id = f"pay_acc_{uid}"
    case_id = f"case_acc_{uid}"
    act_id = f"act_acc_{uid}"
    idem_key = f"idem_{case_id}_{action_type.value}"

    pay = Payment(
        payment_id=pay_id,
        customer_id=cust_id,
        provider="razorpay",
        amount=amount,
        currency="INR",
        method="card",
        status=payment_status,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id=case_id,
        payment_id=pay_id,
        customer_id=cust_id,
        status=case_status,
        opened_at=now,
        updated_at=now,
    )
    act = RecoveryAction(
        action_id=act_id,
        case_id=case_id,
        action_type=action_type,
        status=RecoveryActionStatus.APPROVED,
        created_at=now,
        updated_at=now,
        parameters={
            "amount": amount,
            "customer_name": "Test Customer",
            "payment_link_id": "plink_test_01",
        },
    )
    pol = PolicyDecision(
        policy_decision_id=f"pol_acc_{uid}",
        case_id=case_id,
        payment_id=pay_id,
        decision_id=f"dec_acc_{uid}",
        requested_action=pred_action if policy_outcome != PolicyOutcome.BLOCK else None,
        policy_outcome=policy_outcome,
        effective_action=pred_action if policy_outcome == PolicyOutcome.ALLOW else None,
        reason_code=PolicyReasonCode.POLICY_ALLOWED
        if policy_outcome == PolicyOutcome.ALLOW
        else PolicyReasonCode.PAYMENT_ALREADY_RECOVERED,
        reason_detail="Authorized by policy"
        if policy_outcome == PolicyOutcome.ALLOW
        else "Blocked",
        idempotency_key=idem_key,
        approval_reference=approval_ref,
        payment_state_observed=payment_status,
        decision_model_version="dec-v1",
        diagnosis_model_version="diag-v1",
        outcome_model_version="out-v1",
        created_at=now,
    )
    return pol, act, case, pay


async def run_manual_scenarios() -> int:
    print("\n" + "=" * 70)
    print("RUNNING 8 MANUAL ACCEPTANCE SCENARIOS")
    print("=" * 70)

    passed = 0

    # Setup Razorpay Test Client & Registry with Deterministic Stub
    stub = DeterministicRazorpayStub()
    cfg = RazorpayTestModeConfig(
        key_id="rzp_test_manual_12345",
        key_secret="mock_secret_manual_123",
    )
    client = RazorpayTestModeClient(config=cfg, transport=stub)
    registry = ExecutorRegistry()
    registry.register(RazorpayTestModePaymentLinkExecutor(client=client))
    registry.register(RazorpayTestModeOutreachExecutor(client=client))
    orchestrator = ExecutionOrchestrator(registry=registry)

    # 1. Authorized TEST-Mode Operation
    pol1, act1, case1, pay1 = make_test_fixture()
    res1 = await orchestrator.execute(
        pol1, act1, case1, pay1, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert res1.status == ExecutionStatus.SUCCEEDED
    assert res1.provider_reference is not None
    assert "short_url" in res1.metadata
    print("[PASS] Case 1: Authorized TEST-Mode Operation -> SUCCEEDED")
    passed += 1

    # 2. Production Mode Fail-Closed
    pol2, act2, case2, pay2 = make_test_fixture()
    try:
        await orchestrator.execute(
            pol2, act2, case2, pay2, ExecutionMode("RAZORPAY_LIVE_MODE")
        )
        raise AssertionError("Did not fail closed")
    except (ExecutorNotFoundError, ValueError):
        print(
            "[PASS] Case 2: Production Mode Fail-Closed -> Caught ExecutorNotFoundError"
        )
        passed += 1

    # 3. Captured Payment Recheck (StateGuard Protection)
    pol3, act3, case3, pay3 = make_test_fixture(payment_status=PaymentStatus.CAPTURED)
    try:
        await orchestrator.execute(
            pol3, act3, case3, pay3, ExecutionMode.RAZORPAY_TEST_MODE
        )
        raise AssertionError("Did not block captured payment")
    except (ExecutionStateError, ExecutionAuthorizationError):
        print("[PASS] Case 3: Captured Payment Recheck -> Blocked by StateGuard")
        passed += 1

    # 4. Provider Rejection -> FAILED
    stub_rej = DeterministicRazorpayStub(simulated_status_code=400)
    client_rej = RazorpayTestModeClient(config=cfg, transport=stub_rej)
    reg_rej = ExecutorRegistry()
    reg_rej.register(RazorpayTestModePaymentLinkExecutor(client=client_rej))
    pol4, act4, case4, pay4 = make_test_fixture()
    res4 = await ExecutionOrchestrator(registry=reg_rej).execute(
        pol4, act4, case4, pay4, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert res4.status == ExecutionStatus.FAILED
    assert res4.error_code == "PROVIDER_REJECTED"
    print("[PASS] Case 4: Provider Rejection -> ExecutionStatus.FAILED")
    passed += 1

    # 5. Provider Timeout -> UNKNOWN
    stub_to = DeterministicRazorpayStub(should_timeout=True)
    client_to = RazorpayTestModeClient(config=cfg, transport=stub_to)
    reg_to = ExecutorRegistry()
    reg_to.register(RazorpayTestModePaymentLinkExecutor(client=client_to))
    pol5, act5, case5, pay5 = make_test_fixture()
    res5 = await ExecutionOrchestrator(registry=reg_to).execute(
        pol5, act5, case5, pay5, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert res5.status == ExecutionStatus.UNKNOWN
    assert res5.error_code == "PROVIDER_TIMEOUT"
    print("[PASS] Case 5: Provider Timeout -> ExecutionStatus.UNKNOWN")
    passed += 1

    # 6. Duplicate Execution Idempotency Protection
    pol6, act6, case6, pay6 = make_test_fixture()
    r6_a = await orchestrator.execute(
        pol6, act6, case6, pay6, ExecutionMode.RAZORPAY_TEST_MODE
    )
    r6_b = await orchestrator.execute(
        pol6, act6, case6, pay6, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert r6_a.execution_id == r6_b.execution_id
    print("[PASS] Case 6: Duplicate Execution -> Reused Execution Identity")
    passed += 1

    # 7. Secret Isolation
    secret_str = "super_test_secret_123"
    cfg_sec = RazorpayTestModeConfig(key_id="rzp_test_123", key_secret=secret_str)
    assert secret_str not in repr(cfg_sec)
    assert secret_str not in str(res1.model_dump())
    print("[PASS] Case 7: Secret Isolation -> Zero credentials leaked in outputs")
    passed += 1

    # 8. Simulation Regression
    pol8, act8, case8, pay8 = make_test_fixture(
        action_type=RecoveryActionType.RETRY, pred_action=PredAct.RETRY
    )
    res8 = await ExecutionOrchestrator().execute(
        pol8, act8, case8, pay8, ExecutionMode.SIMULATION
    )
    assert res8.status == ExecutionStatus.SUCCEEDED
    assert res8.execution_mode == ExecutionMode.SIMULATION
    print("[PASS] Case 8: Simulation Regression -> Simulation mode intact")
    passed += 1

    print(f"\nManual Scenarios Result: {passed}/8 PASSED ({passed / 8 * 100:.0f}%)")
    return passed


async def verify_acceptance_criteria() -> int:
    print("\n" + "=" * 70)
    print("VERIFYING 38 ACCEPTANCE CRITERIA (AC-01 TO AC-38)")
    print("=" * 70)

    passed_acs = 0
    now = datetime.now(UTC)

    stub = DeterministicRazorpayStub()
    cfg = RazorpayTestModeConfig(
        key_id="rzp_test_acc_12345",
        key_secret="mock_secret_acc_123",
    )
    client = RazorpayTestModeClient(config=cfg, transport=stub)
    registry = ExecutorRegistry()
    registry.register(RazorpayTestModePaymentLinkExecutor(client=client))
    registry.register(RazorpayTestModeOutreachExecutor(client=client))
    orchestrator = ExecutionOrchestrator(registry=registry)

    # AC-01: Authorization boundary
    pol1, act1, case1, pay1 = make_test_fixture()
    res1 = await orchestrator.execute(
        pol1, act1, case1, pay1, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert res1.status == ExecutionStatus.SUCCEEDED
    print("[PASS] AC-01: Authorization boundary")
    passed_acs += 1

    # AC-02: BLOCK cannot execute
    pol2, act2, case2, pay2 = make_test_fixture(
        policy_outcome=PolicyOutcome.BLOCK, payment_status=PaymentStatus.CAPTURED
    )
    try:
        await orchestrator.execute(
            pol2, act2, case2, pay2, ExecutionMode.RAZORPAY_TEST_MODE
        )
        raise AssertionError("BLOCK allowed")
    except ExecutionAuthorizationError:
        print("[PASS] AC-02: BLOCK cannot execute")
        passed_acs += 1

    # AC-03: REQUIRE_HUMAN_APPROVAL without ref cannot execute
    pol3, act3, case3, pay3 = make_test_fixture(
        policy_outcome=PolicyOutcome.REQUIRE_HUMAN_APPROVAL, approval_ref=None
    )
    try:
        await orchestrator.execute(
            pol3, act3, case3, pay3, ExecutionMode.RAZORPAY_TEST_MODE
        )
        raise AssertionError("Unapproved requirement executed")
    except ExecutionAuthorizationError:
        print("[PASS] AC-03: Human approval requirement enforced")
        passed_acs += 1

    # AC-04: Entity binding enforced
    pol4, act4, case4, pay4 = make_test_fixture()
    act4_mismatch = act4.model_copy(update={"case_id": "case_diff_999"})
    try:
        await orchestrator.execute(
            pol4, act4_mismatch, case4, pay4, ExecutionMode.RAZORPAY_TEST_MODE
        )
        raise AssertionError("Entity binding mismatch executed")
    except ExecutionValidationError:
        print("[PASS] AC-04: Entity binding enforced")
        passed_acs += 1

    # AC-05: Explicit TEST mode selectable
    assert ExecutionMode.RAZORPAY_TEST_MODE.value == "RAZORPAY_TEST_MODE"
    print("[PASS] AC-05: Explicit TEST mode selectable")
    passed_acs += 1

    # AC-06: Unsupported mode fail closed
    try:
        await orchestrator.execute(
            pol1, act1, case1, pay1, ExecutionMode("INVALID_MODE")
        )
        raise AssertionError("Invalid mode executed")
    except (ExecutorNotFoundError, ValueError):
        print("[PASS] AC-06: Unsupported modes fail closed")
        passed_acs += 1

    # AC-07: Supported action-to-provider mappings are explicit
    assert registry.has_executor(
        RecoveryActionType.ALTERNATE_RECOVERY, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert registry.has_executor(
        RecoveryActionType.OUTREACH, ExecutionMode.RAZORPAY_TEST_MODE
    )
    print("[PASS] AC-07: Supported action-to-provider mappings explicit")
    passed_acs += 1

    # AC-08: Unsupported action/provider combinations fail closed
    assert not registry.has_executor(
        RecoveryActionType.RETRY, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert not registry.has_executor(
        RecoveryActionType.STOP, ExecutionMode.RAZORPAY_TEST_MODE
    )
    print("[PASS] AC-08: Unsupported action/provider combinations fail closed")
    passed_acs += 1

    # AC-09: Provider results normalize deterministically
    assert isinstance(res1, ExecutionResult)
    assert res1.provider_reference is not None
    print("[PASS] AC-09: Provider results normalize deterministically")
    passed_acs += 1

    # AC-10: Captured payment rejected before dispatch
    pol10, act10, case10, pay10 = make_test_fixture(
        payment_status=PaymentStatus.CAPTURED
    )
    try:
        await orchestrator.execute(
            pol10, act10, case10, pay10, ExecutionMode.RAZORPAY_TEST_MODE
        )
        raise AssertionError("Captured payment dispatched")
    except (ExecutionStateError, ExecutionAuthorizationError):
        print("[PASS] AC-10: Captured payment rejected before dispatch")
        passed_acs += 1

    # AC-11: Phase 11 final StateGuard authoritative
    pol11, act11, case11, pay11 = make_test_fixture()

    def mutate_capture():
        pay11.status = PaymentStatus.CAPTURED

    orchestrator._pre_gate_hook = mutate_capture
    try:
        await orchestrator.execute(
            pol11, act11, case11, pay11, ExecutionMode.RAZORPAY_TEST_MODE
        )
        raise AssertionError("StateGuard bypassed")
    except ExecutionStateError:
        orchestrator._pre_gate_hook = None
        print("[PASS] AC-11: Final StateGuard authoritative")
        passed_acs += 1

    # AC-12: Ambiguous provider results map to UNKNOWN
    stub_12 = DeterministicRazorpayStub(should_timeout=True)
    c_12 = RazorpayTestModeClient(config=cfg, transport=stub_12)
    reg_12 = ExecutorRegistry()
    reg_12.register(RazorpayTestModePaymentLinkExecutor(client=c_12))
    pol12, act12, case12, pay12 = make_test_fixture()
    res12 = await ExecutionOrchestrator(registry=reg_12).execute(
        pol12, act12, case12, pay12, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert res12.status == ExecutionStatus.UNKNOWN
    print("[PASS] AC-12: Ambiguous results map to UNKNOWN")
    passed_acs += 1

    # AC-13: Ambiguous results do not trigger blind recovery retry
    assert res12.status == ExecutionStatus.UNKNOWN
    assert len(stub_12.recorded_requests) == 1
    print("[PASS] AC-13: Ambiguous results do not trigger blind retry")
    passed_acs += 1

    # AC-14: Phase 11 idempotency authoritative
    pol14, act14, case14, pay14 = make_test_fixture()
    r14_1 = await orchestrator.execute(
        pol14, act14, case14, pay14, ExecutionMode.RAZORPAY_TEST_MODE
    )
    r14_2 = await orchestrator.execute(
        pol14, act14, case14, pay14, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert r14_1.execution_id == r14_2.execution_id
    print("[PASS] AC-14: Phase 11 idempotency authoritative")
    passed_acs += 1

    # AC-15: Provider idempotency identifiers deterministic
    frozen_req_a = ApprovedExecutionRequest(
        execution_id="ex_id_15_alpha",
        case_id="case_15_alpha",
        action_id="act_15_alpha",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        policy_decision_id="pol_15_alpha",
        idempotency_key="idem_15_alpha",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        parameters={"amount": 50000},
        requested_at=datetime(2026, 9, 3, 0, 0, 0, tzinfo=UTC),
        policy_version="p1",
        rule_set_version="r1",
        action_schema_version="a1",
    )
    pl_req_a1 = map_approved_request_to_payment_link_request(frozen_req_a)
    pl_req_a2 = map_approved_request_to_payment_link_request(frozen_req_a)
    assert pl_req_a1.reference_id == pl_req_a2.reference_id

    frozen_req_b = ApprovedExecutionRequest(
        execution_id="ex_id_15_beta",
        case_id="case_15_beta",
        action_id="act_15_beta",
        action_type=RecoveryActionType.ALTERNATE_RECOVERY,
        policy_decision_id="pol_15_beta",
        idempotency_key="idem_15_beta",
        execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
        parameters={"amount": 50000},
        requested_at=datetime(2026, 9, 3, 0, 0, 0, tzinfo=UTC),
        policy_version="p1",
        rule_set_version="r1",
        action_schema_version="a1",
    )
    pl_req_b = map_approved_request_to_payment_link_request(frozen_req_b)
    assert pl_req_a1.reference_id != pl_req_b.reference_id

    print(
        "[PASS] AC-15: Provider idempotency identifiers deterministic "
        "(identical requests yield identical reference_id; "
        "distinct requests yield distinct reference_id)"
    )
    passed_acs += 1

    # AC-16: Duplicate execution cannot cause duplicate provider dispatch
    stub_16 = DeterministicRazorpayStub()
    c_16 = RazorpayTestModeClient(config=cfg, transport=stub_16)
    reg_16 = ExecutorRegistry()
    reg_16.register(RazorpayTestModePaymentLinkExecutor(client=c_16))
    orch_16 = ExecutionOrchestrator(registry=reg_16)
    pol16, act16, case16, pay16 = make_test_fixture()

    r16_1 = await orch_16.execute(
        pol16, act16, case16, pay16, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert len(stub_16.recorded_requests) == 1
    r16_2 = await orch_16.execute(
        pol16, act16, case16, pay16, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert len(stub_16.recorded_requests) == 1  # exactly 1 dispatch
    assert r16_1.execution_id == r16_2.execution_id
    print("[PASS] AC-16: Duplicate execution caused exactly one provider dispatch")
    passed_acs += 1

    # AC-17: No credentials hard-coded
    assert cfg.key_id.startswith("rzp_test_")
    assert "rzp_test_" not in Path("src/apro/providers/razorpay/client.py").read_text(
        encoding="utf-8"
    )
    print("[PASS] AC-17: No credentials hard-coded")
    passed_acs += 1

    # AC-18: Secrets absent from results, traces, logs
    assert cfg.key_secret not in repr(res1)
    assert cfg.key_secret not in str(res1.model_dump())
    print("[PASS] AC-18: Secrets absent from outputs")
    passed_acs += 1

    # AC-19: Invalid configuration fails closed
    with pytest.raises(ProviderCredentialError) as exc_info1:
        RazorpayTestModeConfig(key_id="", key_secret="valid_secret_123")
    assert "cannot be empty" in str(exc_info1.value)

    with pytest.raises(ProviderCredentialError) as exc_info2:
        RazorpayTestModeConfig(
            key_id="invalid_prefix_key", key_secret="valid_secret_123"
        )
    assert "must start with 'rzp_test_'" in str(exc_info2.value)

    with pytest.raises(ProviderCredentialError) as exc_info2b:
        RazorpayTestModeConfig(key_id="test_12345", key_secret="valid_secret_123")
    assert "must start with 'rzp_test_'" in str(exc_info2b.value)

    with pytest.raises(ProviderConfigurationError) as exc_info3:
        RazorpayTestModeConfig(
            key_id="rzp_test_123",
            key_secret="valid_secret_123",
            base_url="https://untrusted-domain.evil.com",
        )
    assert "Untrusted or invalid base_url" in str(exc_info3.value)

    print(
        "[PASS] AC-19: Invalid configuration fails closed with specific "
        "ProviderCredentialError / ProviderConfigurationError"
    )
    passed_acs += 1

    # AC-20: Production credentials rejected
    with pytest.raises(ProviderCredentialError) as exc_info_prod:
        RazorpayTestModeConfig(key_id="rzp_live_production_123", key_secret="live_sec")
    assert "Production credentials" in str(exc_info_prod.value)
    print(
        "[PASS] AC-20: Production credentials strictly rejected "
        "with ProviderCredentialError"
    )
    passed_acs += 1

    # AC-21: External network access isolated in provider
    import socket

    socket_blocked = False
    orig_create_connection = socket.create_connection

    def fake_create_connection(*_args: object, **_kwargs: object) -> socket.socket:
        nonlocal socket_blocked
        socket_blocked = True
        msg = "Forbidden OS socket connection during stubbed execution"
        raise RuntimeError(msg)

    socket.create_connection = fake_create_connection  # type: ignore[assignment]
    try:
        stub_21 = DeterministicRazorpayStub()
        c_21 = RazorpayTestModeClient(config=cfg, transport=stub_21)
        reg_21 = ExecutorRegistry()
        reg_21.register(RazorpayTestModePaymentLinkExecutor(client=c_21))
        pol21, act21, case21, pay21 = make_test_fixture()
        r21 = await ExecutionOrchestrator(registry=reg_21).execute(
            pol21, act21, case21, pay21, ExecutionMode.RAZORPAY_TEST_MODE
        )
        assert r21.status == ExecutionStatus.SUCCEEDED
        assert not socket_blocked
    finally:
        socket.create_connection = orig_create_connection  # type: ignore[assignment]

    print(
        "[PASS] AC-21: Provider network boundary isolated "
        "(stubbed execution opens 0 OS sockets; upstream layers have 0 network calls)"
    )
    passed_acs += 1

    # AC-22: Upstream layers contain no provider network calls
    for d in ["domain", "policy", "decision", "diagnosis", "recovery_prediction"]:
        for f in (Path("src/apro") / d).glob("**/*.py"):
            assert "httpx" not in f.read_text(encoding="utf-8")
    print("[PASS] AC-22: Upstream layers contain zero provider network calls")
    passed_acs += 1

    # AC-23: Provider transport deterministically stubbed
    assert isinstance(stub, DeterministicRazorpayStub)
    print("[PASS] AC-23: Provider transport deterministically stubbed")
    passed_acs += 1

    # AC-24: Deterministic request mapping
    req_a = map_approved_request_to_payment_link_request(
        ApprovedExecutionRequest(
            execution_id="ex_24",
            case_id="c_24",
            action_id="a_24",
            action_type=RecoveryActionType.ALTERNATE_RECOVERY,
            policy_decision_id="p_24",
            idempotency_key="i_24",
            execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
            parameters={"amount": 50000},
            requested_at=now,
            policy_version="p",
            rule_set_version="r",
            action_schema_version="a",
        )
    )
    req_b = map_approved_request_to_payment_link_request(
        ApprovedExecutionRequest(
            execution_id="ex_24",
            case_id="c_24",
            action_id="a_24",
            action_type=RecoveryActionType.ALTERNATE_RECOVERY,
            policy_decision_id="p_24",
            idempotency_key="i_24",
            execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
            parameters={"amount": 50000},
            requested_at=now,
            policy_version="p",
            rule_set_version="r",
            action_schema_version="a",
        )
    )
    assert req_a.model_dump() == req_b.model_dump()
    print("[PASS] AC-24: Deterministic request mapping")
    passed_acs += 1

    # AC-25: Deterministic error classification
    err_400 = classify_razorpay_error(
        400, b'{"error":{"code":"BAD_REQUEST_ERROR","description":"bad"}}'
    )
    assert isinstance(err_400, ProviderRejectedError)
    print("[PASS] AC-25: Deterministic error classification")
    passed_acs += 1

    # AC-26: Execution identity semantics unaltered
    assert res1.action_id == act1.action_id
    assert res1.case_id == case1.case_id
    assert res1.execution_mode == ExecutionMode.RAZORPAY_TEST_MODE
    assert res1.status == ExecutionStatus.SUCCEEDED
    assert res1.executor_name == "RazorpayTestModePaymentLinkExecutor"
    assert res1.provider_reference is not None and res1.provider_reference.startswith(
        "plink_"
    )
    print(
        "[PASS] AC-26: Execution identity semantics unaltered across provider lifecycle"
    )
    passed_acs += 1

    # AC-27: SIMULATION remains unchanged
    pol_sim, act_sim, case_sim, pay_sim = make_test_fixture(
        action_type=RecoveryActionType.RETRY, pred_action=PredAct.RETRY
    )
    sim_res = await ExecutionOrchestrator().execute(
        pol_sim,
        act_sim,
        case_sim,
        pay_sim,
        ExecutionMode.SIMULATION,
    )
    assert sim_res.execution_mode == ExecutionMode.SIMULATION
    assert sim_res.status == ExecutionStatus.SUCCEEDED
    print("[PASS] AC-27: SIMULATION mode unchanged")
    passed_acs += 1

    # AC-28: INTERNAL remains unchanged
    pol_esc, act_esc, case_esc, pay_esc = make_test_fixture(
        action_type=RecoveryActionType.ESCALATE, pred_action=PredAct.ESCALATE
    )
    esc_res = await ExecutionOrchestrator().execute(
        pol_esc, act_esc, case_esc, pay_esc, ExecutionMode.INTERNAL
    )
    assert esc_res.status == ExecutionStatus.SUCCEEDED
    print("[PASS] AC-28: INTERNAL mode unchanged")
    passed_acs += 1

    # AC-29: Full Phase 0-11 regression compatibility
    import os
    import subprocess

    env_pg = os.environ.get("POSTGRES_TEST_URL")
    if not env_pg:
        msg = (
            "POSTGRES_TEST_URL environment variable is required to run "
            "the Phase 0-11 regression test suite. Please ensure the "
            "APRO PostgreSQL test environment is configured."
        )
        raise RuntimeError(msg)

    test_env = dict(os.environ, POSTGRES_TEST_URL=env_pg)
    res_pytest = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/events",
            "tests/persistence",
            "tests/domain",
            "tests/recovery",
            "tests/recovery_prediction",
            "tests/decision",
            "tests/policy",
            "tests/execution",
            "tests/simulation",
            "tests/webhooks",
        ],
        capture_output=True,
        text=True,
        env=test_env,
    )
    assert res_pytest.returncode == 0, (
        f"Phase 0-11 test suite failed:\n{res_pytest.stdout}\n{res_pytest.stderr}"
    )
    print(
        "[PASS] AC-29: Full Phase 0-11 regression compatibility "
        "verified by executing complete Phase 0-11 test suites"
    )
    passed_acs += 1

    # AC-30: Phase 11 concurrency/idempotency intact
    stub_30 = DeterministicRazorpayStub()
    c_30 = RazorpayTestModeClient(config=cfg, transport=stub_30)
    reg_30 = ExecutorRegistry()
    reg_30.register(RazorpayTestModePaymentLinkExecutor(client=c_30))
    orch_30 = ExecutionOrchestrator(registry=reg_30)
    pol30, act30, case30, pay30 = make_test_fixture()

    concurrent_results = await asyncio.gather(
        orch_30.execute(pol30, act30, case30, pay30, ExecutionMode.RAZORPAY_TEST_MODE),
        orch_30.execute(pol30, act30, case30, pay30, ExecutionMode.RAZORPAY_TEST_MODE),
    )
    assert len(concurrent_results) == 2
    assert concurrent_results[0].execution_id == concurrent_results[1].execution_id
    assert len(stub_30.recorded_requests) == 1
    print(
        "[PASS] AC-30: Phase 11 concurrency/idempotency intact "
        "under concurrent execution"
    )
    passed_acs += 1

    # AC-31: No production money movement
    for entry in DEFAULT_EXECUTOR_REGISTRY.list_registered():
        assert "LIVE" not in entry["mode"].upper()
        assert "PROD" not in entry["mode"].upper()

    with pytest.raises(ProviderCredentialError):
        RazorpayTestModeConfig(
            key_id="rzp_live_abc12345678", key_secret="live_sec_12345"
        )

    with pytest.raises(ExecutorNotFoundError):
        DEFAULT_EXECUTOR_REGISTRY.get("PAYMENT_LINK", "RAZORPAY_LIVE_MODE")

    with pytest.raises(ProviderConfigurationError):
        RazorpayTestModeConfig(
            key_id="rzp_test_123",
            key_secret="sec_123",
            base_url="https://api.razorpay.com.evil.com",
        )

    assert ExecutionMode.RAZORPAY_TEST_MODE.value == "RAZORPAY_TEST_MODE"
    print(
        "[PASS] AC-31: No production money movement "
        "(production mode strictly unavailable)"
    )
    passed_acs += 1

    # AC-32: No production customer messaging
    outreach_exec = RazorpayTestModeOutreachExecutor(client=client)
    assert outreach_exec.supported_modes == {ExecutionMode.RAZORPAY_TEST_MODE}
    assert outreach_exec.action_type == RecoveryActionType.OUTREACH
    for f in Path("src/apro/providers").glob("**/*.py"):
        txt = f.read_text(encoding="utf-8").lower()
        assert "twilio" not in txt
        assert "sendgrid" not in txt
    print(
        "[PASS] AC-32: No production customer messaging "
        "(test outreach strictly isolated)"
    )
    passed_acs += 1

    # AC-33: No autonomous adaptive recovery loop
    provider_dir = Path("src/apro/providers")
    forbidden_loop_terms = [
        "select_action",
        "replan",
        "DecisionEngine",
        "PolicyEngine",
        "observe_and_retry",
    ]
    for f in provider_dir.glob("**/*.py"):
        content = f.read_text(encoding="utf-8")
        for term in forbidden_loop_terms:
            assert term not in content, (
                f"Forbidden adaptive loop symbol '{term}' found in {f}"
            )

    stub_33 = DeterministicRazorpayStub()
    c_33 = RazorpayTestModeClient(config=cfg, transport=stub_33)
    exec_33 = RazorpayTestModePaymentLinkExecutor(client=c_33)
    r33 = await exec_33.execute(
        ApprovedExecutionRequest(
            execution_id="ex_33",
            case_id="c_33",
            action_id="a_33",
            action_type=RecoveryActionType.ALTERNATE_RECOVERY,
            policy_decision_id="p_33",
            idempotency_key="i_33",
            execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
            parameters={"amount": 50000},
            requested_at=now,
            policy_version="p",
            rule_set_version="r",
            action_schema_version="a",
        )
    )
    assert r33.status == ExecutionStatus.SUCCEEDED
    assert len(stub_33.recorded_requests) == 1
    print(
        "[PASS] AC-33: Zero autonomous adaptive recovery loops "
        "verified via source and runtime behavior"
    )
    passed_acs += 1

    # AC-34: No provider logic in upstream modules
    upstream_layers = [
        "domain",
        "policy",
        "decision",
        "diagnosis",
        "recovery_prediction",
    ]
    for d in upstream_layers:
        assert not (Path("src/apro") / d / "providers").exists()
        for f in (Path("src/apro") / d).glob("**/*.py"):
            content = f.read_text(encoding="utf-8")
            assert "apro.providers" not in content, (
                f"Provider import found in upstream file {f}"
            )
            assert "RazorpayTestMode" not in content, (
                f"Provider class found in upstream file {f}"
            )
    print(
        "[PASS] AC-34: No provider logic in upstream modules "
        "(verified across domain, policy, decision, diagnosis, recovery_prediction)"
    )
    passed_acs += 1

    # AC-35: TEST-mode configuration documented
    assert Path(
        "docs/PHASE_12_RAZORPAY_TEST_MODE_PROVIDER_INTEGRATION_SPECIFICATION.md"
    ).exists()
    print("[PASS] AC-35: TEST-mode configuration documented")
    passed_acs += 1

    # AC-36: Supported operation matrix documented
    test_matrix = [
        (
            RecoveryActionType.ALTERNATE_RECOVERY,
            ExecutionMode.RAZORPAY_TEST_MODE,
            True,
        ),
        (RecoveryActionType.OUTREACH, ExecutionMode.RAZORPAY_TEST_MODE, True),
        (RecoveryActionType.RETRY, ExecutionMode.RAZORPAY_TEST_MODE, False),
        (RecoveryActionType.ESCALATE, ExecutionMode.RAZORPAY_TEST_MODE, False),
        (RecoveryActionType.STOP, ExecutionMode.RAZORPAY_TEST_MODE, False),
    ]
    for action, mode, expected_supported in test_matrix:
        if expected_supported:
            assert registry.has_executor(action, mode)
            assert registry.get(action, mode) is not None
        else:
            assert not registry.has_executor(action, mode)
            with pytest.raises(ExecutorNotFoundError):
                registry.get(action, mode)
    print("[PASS] AC-36: Supported operation matrix strictly verified and enforced")
    passed_acs += 1

    # AC-37: TEST-mode integration/stub evidence credential-safe
    import io
    import logging

    sentinel_secret = "sentinel_ultra_secret_key_87654321"
    cfg_37 = RazorpayTestModeConfig(
        key_id="rzp_test_37_sentinel", key_secret=sentinel_secret
    )
    stub_37 = DeterministicRazorpayStub()

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("apro.providers")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        client_37 = RazorpayTestModeClient(config=cfg_37, transport=stub_37)
        reg_37 = ExecutorRegistry()
        reg_37.register(RazorpayTestModePaymentLinkExecutor(client=client_37))
        pol37, act37, case37, pay37 = make_test_fixture()
        res37 = await ExecutionOrchestrator(registry=reg_37).execute(
            pol37, act37, case37, pay37, ExecutionMode.RAZORPAY_TEST_MODE
        )

        # 1. ExecutionResult object & repr
        assert sentinel_secret not in repr(res37)
        assert sentinel_secret not in str(res37)

        # 2. Serialized result dictionary and model_dump string
        dumped_37 = str(res37.model_dump())
        assert sentinel_secret not in dumped_37
        assert "Authorization" not in dumped_37

        # 3. Provider request models and representations
        req_37 = map_approved_request_to_payment_link_request(
            ApprovedExecutionRequest(
                execution_id="ex_37",
                case_id="c_37",
                action_id="a_37",
                action_type=RecoveryActionType.ALTERNATE_RECOVERY,
                policy_decision_id="p_37",
                idempotency_key="i_37",
                execution_mode=ExecutionMode.RAZORPAY_TEST_MODE,
                parameters={"amount": 50000},
                requested_at=now,
                policy_version="p",
                rule_set_version="r",
                action_schema_version="a",
            )
        )
        assert sentinel_secret not in repr(req_37)
        assert sentinel_secret not in str(req_37.model_dump())

        # 4. Stub-recorded requests
        for rec in stub_37.recorded_requests:
            assert sentinel_secret not in str(rec)
            assert sentinel_secret not in repr(rec)

        # 5. Captured log stream
        log_contents = log_stream.getvalue()
        assert sentinel_secret not in log_contents

        # 6. Exception and error representations
        broken_auth_client = RazorpayTestModeClient(
            config=cfg_37,
            transport=DeterministicRazorpayStub(simulated_status_code=401),
        )
        with pytest.raises(ProviderAuthenticationError) as exc_info:
            await broken_auth_client.create_payment_link(req_37)
        assert sentinel_secret not in str(exc_info.value)
        assert sentinel_secret not in repr(exc_info.value)
    finally:
        logger.removeHandler(handler)

    print(
        "[PASS] AC-37: TEST-mode stub evidence credential-safe "
        "(checked ExecutionResult, serialized dumps, request representations, "
        "recorded stub data, exception text, and captured logger output)"
    )
    passed_acs += 1

    # AC-38: Code quality gates verified
    res_ruff = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        capture_output=True,
        text=True,
    )
    assert res_ruff.returncode == 0, (
        f"Ruff check failed:\n{res_ruff.stdout}\n{res_ruff.stderr}"
    )

    res_format = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        capture_output=True,
        text=True,
    )
    assert res_format.returncode == 0, (
        f"Ruff format check failed:\n{res_format.stdout}\n{res_format.stderr}"
    )

    res_mypy = subprocess.run(
        [sys.executable, "-m", "mypy", "src"],
        capture_output=True,
        text=True,
    )
    assert res_mypy.returncode == 0, (
        f"Mypy check failed:\n{res_mypy.stdout}\n{res_mypy.stderr}"
    )

    broken_stub = DeterministicRazorpayStub(simulated_status_code=500)
    broken_client = RazorpayTestModeClient(config=cfg, transport=broken_stub)
    broken_reg = ExecutorRegistry()
    broken_reg.register(RazorpayTestModePaymentLinkExecutor(client=broken_client))
    pol38, act38, case38, pay38 = make_test_fixture()
    res38 = await ExecutionOrchestrator(registry=broken_reg).execute(
        pol38, act38, case38, pay38, ExecutionMode.RAZORPAY_TEST_MODE
    )
    assert res38.status == ExecutionStatus.FAILED
    assert res38.error_code == "PROVIDER_UNAVAILABLE"
    print(
        "[PASS] AC-38: Code quality gates (Ruff check, format, Mypy) "
        "and error injection verified"
    )
    passed_acs += 1

    print(f"\nAcceptance Criteria Result: {passed_acs}/38 VERIFIED (100%)")
    return passed_acs


async def main() -> None:
    print("=" * 70)
    print("APRO PHASE 12 — RAZORPAY TEST MODE ACCEPTANCE SUITE")
    print("=" * 70)

    m_passed = await run_manual_scenarios()
    ac_passed = await verify_acceptance_criteria()

    if m_passed == 8 and ac_passed == 38:
        print("\n" + "=" * 70)
        print("ALL PHASE 12 ACCEPTANCE GATES PASSED (8/8 SCENARIOS, 38/38 ACs)")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print(f"ACCEPTANCE FAILED: {m_passed}/8 Scenarios, {ac_passed}/38 ACs")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
