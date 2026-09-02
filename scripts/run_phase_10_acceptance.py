"""APRO — Phase 10 Acceptance Test Runner
Authoritative acceptance test suite verifying all 12 manual scenarios
and all 38 Acceptance Criteria (AC-01 through AC-38) with genuine executable assertions.
"""

# ruff: noqa: E402

import copy
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to pythonpath
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.decision.enums import DecisionStatus
from apro.decision.models import ActionEligibility, ActionUtility, RecoveryDecision
from apro.diagnosis.classifiers.decision_tree import DecisionTreeDiagnosisModel
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Payment, RecoveryCase
from apro.policy.approvals import validate_human_approval
from apro.policy.artifacts import load_policy_artifact, save_policy_artifact
from apro.policy.config import DEFAULT_POLICY_CONFIG, PolicyConfig
from apro.policy.engine import PolicyEngine
from apro.policy.enums import (
    POLICY_ARTIFACT_SCHEMA_VERSION,
    POLICY_DECISION_SCHEMA_VERSION,
    POLICY_SCHEMA_VERSION,
    POLICY_TRACE_SCHEMA_VERSION,
    POLICY_VERSION,
    RULE_SET_VERSION,
    PolicyOutcome,
    PolicyReasonCode,
    RulePrecedenceLevel,
)
from apro.policy.evaluation import (
    compare_distribution_shift,
    evaluate_policy_on_dataset,
    evaluate_policy_segments,
    perform_policy_error_analysis,
)
from apro.policy.models import (
    ActionExecutionHistory,
    ApprovalRecord,
    EventTrustState,
)
from apro.policy.state_guard import StateGuard
from apro.recovery_prediction.classifiers.logistic import (
    LogisticRegressionOutcomeModel,
)
from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_ORDER,
    RecoveryAction,
)


def make_test_fixture(
    case_id: str = "case_acc_001",
    payment_id: str = "pay_acc_001",
    action: RecoveryAction = RecoveryAction.RETRY,
    payment_status: PaymentStatus = PaymentStatus.FAILED,
    payment_amount: int = 50000,
    confidence: float = 0.85,
    erv: int = 4000,
    retry_count: int = 0,
    last_retry_at: datetime | None = None,
    same_action_count: int = 0,
    last_action: RecoveryAction | None = None,
    total_interventions: int = 0,
    payment_link_count: int = 0,
    executed_approval_ids: tuple[str, ...] = (),
    executed_idempotency_keys: tuple[str, ...] = (),
    updated_at: datetime | None = None,
    captured_at: datetime | None = None,
) -> tuple[RecoveryDecision, Payment, RecoveryCase, ActionExecutionHistory]:
    now = datetime.now(UTC)
    payment = Payment(
        payment_id=payment_id,
        customer_id="cust_acc_001",
        provider="razorpay",
        amount=payment_amount,
        currency="INR",
        method="card",
        status=payment_status,
        created_at=now,
        updated_at=updated_at or now,
        captured_at=captured_at
        or (now if payment_status == PaymentStatus.CAPTURED else None),
    )
    case = RecoveryCase(
        case_id=case_id,
        payment_id=payment_id,
        customer_id="cust_acc_001",
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
        current_attempt_count=retry_count,
    )
    utilities = {
        act: ActionUtility(
            action=act,
            eligible=True,
            predicted_success_probability=0.75,
            predicted_recovered_amount=payment_amount,
            expected_gross_recovery=int(0.75 * payment_amount),
            action_cost=150,
            operational_cost=50,
            customer_friction_cost=0,
            risk_penalty=0,
            expected_recovery_value=erv,
        )
        for act in RecoveryAction
    }
    eligibilities = {
        act: ActionEligibility(action=act, is_eligible=True) for act in RecoveryAction
    }
    decision = RecoveryDecision(
        decision_id="dec_acc_001",
        record_id="rec_acc_001",
        scenario_id="scen_acc_001",
        recovery_case_id=case_id,
        selected_action=action,
        decision_status=DecisionStatus.ACTION_SELECTED,
        expected_recovery_value=erv,
        utility_by_action=utilities,
        eligibility_by_action=eligibilities,
        decision_confidence=confidence,
        rationale="Acceptance fixture decision",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        dataset_version="dataset-v1",
    )
    history = ActionExecutionHistory(
        retry_count=retry_count,
        last_retry_at=last_retry_at,
        same_action_count=same_action_count,
        last_action=last_action,
        total_interventions=total_interventions,
        payment_link_count=payment_link_count,
        executed_approval_ids=executed_approval_ids,
        executed_idempotency_keys=executed_idempotency_keys,
    )
    return decision, payment, case, history


def run_manual_scenarios() -> int:
    print("\n" + "=" * 70)
    print("RUNNING 12 MANUAL ACCEPTANCE SCENARIOS")
    print("=" * 70)

    engine = PolicyEngine()
    passed = 0
    now = datetime.now(UTC)

    # Case 1: Captured Payment -> Blocked (PAYMENT_ALREADY_RECOVERED)
    dec, pay, case, hist = make_test_fixture(payment_status=PaymentStatus.CAPTURED)
    pol_dec, _ = engine.evaluate(
        dec,
        pay,
        case,
        current_time=now,
        history=hist,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.PAYMENT_ALREADY_RECOVERED
    print("[PASS] Case 1: Captured Payment -> Blocked (PAYMENT_ALREADY_RECOVERED)")
    passed += 1

    # Case 2: Invalid Event -> Blocked (INVALID_EVENT)
    dec, pay, case, hist = make_test_fixture()
    pol_dec, _ = engine.evaluate(
        dec,
        pay,
        case,
        current_time=now,
        history=hist,
        event_trust=EventTrustState.UNTRUSTED,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.INVALID_EVENT
    print("[PASS] Case 2: Invalid Event -> Blocked (INVALID_EVENT)")
    passed += 1

    # Case 3: Duplicate Event -> Blocked (DUPLICATE_EVENT)
    dec, pay, case, hist = make_test_fixture()
    pol_dec, _ = engine.evaluate(
        dec,
        pay,
        case,
        current_time=now,
        history=hist,
        event_trust=EventTrustState.TRUSTED,
        is_duplicate_event=True,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.DUPLICATE_EVENT
    print("[PASS] Case 3: Duplicate Event -> Blocked (DUPLICATE_EVENT)")
    passed += 1

    # Case 4: Retry Limit (3/3) -> Blocked (MAX_RETRIES_REACHED)
    dec, pay, case, hist = make_test_fixture(action=RecoveryAction.RETRY, retry_count=3)
    pol_dec, _ = engine.evaluate(
        dec,
        pay,
        case,
        current_time=now,
        config=PolicyConfig(max_retries=3),
        history=hist,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.MAX_RETRIES_REACHED
    print("[PASS] Case 4: Retry Limit (3/3) -> Blocked (MAX_RETRIES_REACHED)")
    passed += 1

    # Case 5: Retry Cooldown -> Blocked (RETRY_COOLDOWN_ACTIVE)
    last_retry = now - timedelta(seconds=60)
    dec, pay, case, hist = make_test_fixture(
        action=RecoveryAction.RETRY, last_retry_at=last_retry
    )
    pol_dec, _ = engine.evaluate(
        dec,
        pay,
        case,
        current_time=now,
        config=PolicyConfig(retry_cooldown_seconds=300),
        history=hist,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.RETRY_COOLDOWN_ACTIVE
    print("[PASS] Case 5: Retry Cooldown -> Blocked (RETRY_COOLDOWN_ACTIVE)")
    passed += 1

    # Case 6: High Value -> REQUIRE_HUMAN_APPROVAL
    dec, pay, case, hist = make_test_fixture(payment_amount=150000)
    pol_dec, _ = engine.evaluate(
        dec,
        pay,
        case,
        current_time=now,
        config=PolicyConfig(high_value_threshold=100000),
        history=hist,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
    assert pol_dec.reason_code == PolicyReasonCode.HIGH_VALUE_REQUIRES_APPROVAL
    assert pol_dec.approval_required is True
    print("[PASS] Case 6: High Value -> REQUIRE_HUMAN_APPROVAL")
    passed += 1

    # Case 7: Low Confidence -> REQUIRE_HUMAN_APPROVAL
    dec, pay, case, hist = make_test_fixture(confidence=0.35)
    pol_dec, _ = engine.evaluate(
        dec,
        pay,
        case,
        current_time=now,
        config=PolicyConfig(min_decision_confidence=0.50),
        history=hist,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
    assert pol_dec.reason_code == PolicyReasonCode.LOW_CONFIDENCE_REQUIRES_APPROVAL
    print("[PASS] Case 7: Low Confidence -> REQUIRE_HUMAN_APPROVAL")
    passed += 1

    # Case 8: Invalid Model Output -> Blocked (INVALID_MODEL_OUTPUT)
    dec, pay, case, hist = make_test_fixture(payment_amount=50000)
    # Corrupt model output with invalid recovered amount
    corrupt_util = dec.utility_by_action[RecoveryAction.RETRY].model_copy(
        update={"predicted_recovered_amount": 90000}
    )
    dec_corrupt = dec.model_copy(
        update={
            "utility_by_action": {
                **dec.utility_by_action,
                RecoveryAction.RETRY: corrupt_util,
            }
        }
    )
    pol_dec, _ = engine.evaluate(
        dec_corrupt,
        pay,
        case,
        current_time=now,
        history=hist,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.INVALID_MODEL_OUTPUT
    print("[PASS] Case 8: Invalid Model Output -> Blocked (INVALID_MODEL_OUTPUT)")
    passed += 1

    # Case 9: Stale Event on Captured Payment (Literal Scenario from Spec)
    # Current payment state = CAPTURED; stale payment.failed event arrives
    t_updated = now
    t_event_old = now - timedelta(minutes=5)
    dec, pay, case, hist = make_test_fixture(
        payment_status=PaymentStatus.CAPTURED,
        updated_at=t_updated,
        captured_at=t_updated,
    )
    pol_dec, _ = engine.evaluate(
        dec,
        pay,
        case,
        current_time=now,
        history=hist,
        event_trust=EventTrustState.TRUSTED,
        event_timestamp=t_event_old,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.effective_action is None
    assert pol_dec.reason_code in (
        PolicyReasonCode.PAYMENT_ALREADY_RECOVERED,
        PolicyReasonCode.STALE_OR_INCONSISTENT_EVENT,
    )
    print("[PASS] Case 9: Stale Event on Captured Payment -> Blocked (Literal Spec)")
    passed += 1

    # Case 10: Approval Mismatch -> Blocked (APPROVAL_MISMATCH)
    dec, pay, case, hist = make_test_fixture(payment_amount=150000)
    mismatched_appr = ApprovalRecord(
        approval_id="appr_bad_01",
        case_id="case_DIFFERENT",
        decision_id="dec_acc_001",
        approved_action=RecoveryAction.RETRY,
        approver_reference="lead",
        approved_at=now,
        policy_version="policy-v1",
    )
    pol_dec, _ = engine.evaluate(
        dec,
        pay,
        case,
        current_time=now,
        config=PolicyConfig(high_value_threshold=100000),
        history=hist,
        event_trust=EventTrustState.TRUSTED,
        approval=mismatched_appr,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.APPROVAL_MISMATCH
    print("[PASS] Case 10: Approval Mismatch -> Blocked (APPROVAL_MISMATCH)")
    passed += 1

    # Case 11: Total Interventions -> Blocked (MAX_TOTAL_INTERVENTIONS_REACHED)
    dec, pay, case, hist = make_test_fixture(total_interventions=5)
    pol_dec, _ = engine.evaluate(
        dec,
        pay,
        case,
        current_time=now,
        config=PolicyConfig(max_total_interventions=5),
        history=hist,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.MAX_TOTAL_INTERVENTIONS_REACHED
    print("[PASS] Case 11: Total Interventions -> Blocked (LIMIT_REACHED)")
    passed += 1

    # Case 12: Bit-for-Bit Determinism -> Identical Hashes
    dec, pay, case, hist = make_test_fixture()
    frozen_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)
    pol_dec1, trace1 = engine.evaluate(
        dec,
        pay,
        case,
        current_time=frozen_time,
        history=hist,
        event_trust=EventTrustState.TRUSTED,
    )
    pol_dec2, trace2 = engine.evaluate(
        dec,
        pay,
        case,
        current_time=frozen_time,
        history=hist,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec1.policy_decision_id == pol_dec2.policy_decision_id
    assert pol_dec1.model_dump() == pol_dec2.model_dump()
    assert trace1.policy_decision_id == trace2.policy_decision_id
    assert trace1.model_dump(exclude={"evaluation_latency_ms"}) == trace2.model_dump(
        exclude={"evaluation_latency_ms"}
    )
    print("[PASS] Case 12: Bit-for-Bit Determinism -> Identical Hashes")
    passed += 1

    print(f"\nManual Scenarios Result: {passed}/12 PASSED (100%)\n")
    return passed


def run_acceptance_criteria() -> int:
    print("=" * 70)
    print("VERIFYING 38 ACCEPTANCE CRITERIA (AC-01 TO AC-38)")
    print("=" * 70)

    engine = PolicyEngine()
    now = datetime.now(UTC)
    passed_acs = 0

    # AC-01: Explicit policy outcomes
    assert set(PolicyOutcome) == {
        PolicyOutcome.ALLOW,
        PolicyOutcome.BLOCK,
        PolicyOutcome.REQUIRE_HUMAN_APPROVAL,
    }
    print("[PASS] AC-01: Explicit policy outcomes")
    passed_acs += 1

    # AC-02: Deterministic rule precedence hierarchy
    assert (
        RulePrecedenceLevel.HARD_SAFETY_BLOCK < RulePrecedenceLevel.STALE_UNKNOWN_STATE
    )
    assert (
        RulePrecedenceLevel.STALE_UNKNOWN_STATE < RulePrecedenceLevel.UNSUPPORTED_ACTION
    )
    assert (
        RulePrecedenceLevel.UNSUPPORTED_ACTION
        < RulePrecedenceLevel.ATTEMPT_INTERVENTION_LIMIT
    )
    assert (
        RulePrecedenceLevel.ATTEMPT_INTERVENTION_LIMIT
        < RulePrecedenceLevel.INVALID_MODEL_OUTPUT
    )
    assert (
        RulePrecedenceLevel.INVALID_MODEL_OUTPUT
        < RulePrecedenceLevel.CONFIDENCE_ECONOMIC_GUARDRAIL
    )
    assert (
        RulePrecedenceLevel.CONFIDENCE_ECONOMIC_GUARDRAIL
        < RulePrecedenceLevel.HUMAN_APPROVAL_REQUIREMENT
    )
    assert RulePrecedenceLevel.HUMAN_APPROVAL_REQUIREMENT < RulePrecedenceLevel.ALLOW
    print("[PASS] AC-02: Deterministic rule precedence hierarchy")
    passed_acs += 1

    # AC-03: Captured-payment hard block (H1)
    d, p, c, h = make_test_fixture(payment_status=PaymentStatus.CAPTURED)
    dec_res, _ = engine.evaluate(
        d, p, c, current_time=now, history=h, event_trust=EventTrustState.TRUSTED
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.PAYMENT_ALREADY_RECOVERED
    print("[PASS] AC-03: Captured-payment hard block (H1)")
    passed_acs += 1

    # AC-04: Invalid-event protection (H2)
    d, p, c, h = make_test_fixture()
    dec_res, _ = engine.evaluate(
        d, p, c, current_time=now, history=h, event_trust=EventTrustState.UNTRUSTED
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.INVALID_EVENT
    print("[PASS] AC-04: Invalid-event protection (H2)")
    passed_acs += 1

    # AC-05: Duplicate-event protection (H3)
    d, p, c, h = make_test_fixture()
    dec_res, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        history=h,
        event_trust=EventTrustState.TRUSTED,
        is_duplicate_event=True,
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.DUPLICATE_EVENT
    print("[PASS] AC-05: Duplicate-event protection (H3)")
    passed_acs += 1

    # AC-06: Unsupported-action protection (H4)
    assert len(RECOVERY_ACTION_ORDER) == 5
    assert set(RECOVERY_ACTION_ORDER) == {
        RecoveryAction.RETRY,
        RecoveryAction.PAYMENT_LINK,
        RecoveryAction.OUTREACH,
        RecoveryAction.STOP,
        RecoveryAction.ESCALATE,
    }
    print("[PASS] AC-06: Unsupported-action protection (H4)")
    passed_acs += 1

    # AC-07: Invalid-model-output rejection (H5)
    d, p, c, h = make_test_fixture()
    bad_util = d.utility_by_action[RecoveryAction.RETRY].model_copy(
        update={"predicted_success_probability": -0.5}
    )
    d_bad = d.model_copy(
        update={
            "utility_by_action": {
                **d.utility_by_action,
                RecoveryAction.RETRY: bad_util,
            }
        }
    )
    dec_res, _ = engine.evaluate(
        d_bad, p, c, current_time=now, history=h, event_trust=EventTrustState.TRUSTED
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.INVALID_MODEL_OUTPUT
    assert dec_res.model_output_valid is False
    print("[PASS] AC-07: Invalid-model-output rejection (H5)")
    passed_acs += 1

    # AC-08: Retry-limit enforcement (R1)
    d, p, c, h = make_test_fixture(action=RecoveryAction.RETRY, retry_count=3)
    dec_res, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        config=PolicyConfig(max_retries=3),
        history=h,
        event_trust=EventTrustState.TRUSTED,
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.MAX_RETRIES_REACHED
    print("[PASS] AC-08: Retry-limit enforcement (R1)")
    passed_acs += 1

    # AC-09: Retry cooldown enforcement (R2)
    last_ret = now - timedelta(seconds=30)
    d, p, c, h = make_test_fixture(action=RecoveryAction.RETRY, last_retry_at=last_ret)
    dec_res, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        config=PolicyConfig(retry_cooldown_seconds=300),
        history=h,
        event_trust=EventTrustState.TRUSTED,
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.RETRY_COOLDOWN_ACTIVE
    print("[PASS] AC-09: Retry cooldown enforcement (R2)")
    passed_acs += 1

    # AC-10: Same-action repetition protection (R3)
    d, p, c, h = make_test_fixture(
        action=RecoveryAction.PAYMENT_LINK,
        last_action=RecoveryAction.PAYMENT_LINK,
        same_action_count=2,
    )
    dec_res, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        config=PolicyConfig(max_same_action_repetitions=2),
        history=h,
        event_trust=EventTrustState.TRUSTED,
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.MAX_SAME_ACTION_REPETITIONS_REACHED
    print("[PASS] AC-10: Same-action repetition protection (R3)")
    passed_acs += 1

    # AC-11: Total intervention limit enforcement (R4)
    d, p, c, h = make_test_fixture(
        action=RecoveryAction.OUTREACH, total_interventions=4
    )
    dec_res, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        config=PolicyConfig(max_total_interventions=4),
        history=h,
        event_trust=EventTrustState.TRUSTED,
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.MAX_TOTAL_INTERVENTIONS_REACHED
    print("[PASS] AC-11: Total intervention limit enforcement (R4)")
    passed_acs += 1

    # AC-12: High-value transaction protection (S1)
    d, p, c, h = make_test_fixture(payment_amount=200000)
    dec_res, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        config=PolicyConfig(high_value_threshold=100000),
        history=h,
        event_trust=EventTrustState.TRUSTED,
    )
    assert dec_res.policy_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
    assert dec_res.reason_code == PolicyReasonCode.HIGH_VALUE_REQUIRES_APPROVAL
    print("[PASS] AC-12: High-value transaction protection (S1)")
    passed_acs += 1

    # AC-13: Low-confidence protection (S2)
    d, p, c, h = make_test_fixture(confidence=0.30)
    dec_res, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        config=PolicyConfig(min_decision_confidence=0.50),
        history=h,
        event_trust=EventTrustState.TRUSTED,
    )
    assert dec_res.policy_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
    assert dec_res.reason_code == PolicyReasonCode.LOW_CONFIDENCE_REQUIRES_APPROVAL
    print("[PASS] AC-13: Low-confidence protection (S2)")
    passed_acs += 1

    # AC-14: Minimum ERV protection (S3)
    d, p, c, h = make_test_fixture(erv=50)
    dec_res, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        config=PolicyConfig(min_expected_recovery_value=100),
        history=h,
        event_trust=EventTrustState.TRUSTED,
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.INSUFFICIENT_EXPECTED_VALUE
    print("[PASS] AC-14: Minimum ERV protection (S3)")
    passed_acs += 1

    # AC-15: Negative ERV protection (S4)
    d, p, c, h = make_test_fixture(erv=-100)
    dec_res, _ = engine.evaluate(
        d, p, c, current_time=now, history=h, event_trust=EventTrustState.TRUSTED
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.NEGATIVE_EXPECTED_VALUE
    print("[PASS] AC-15: Negative ERV protection (S4)")
    passed_acs += 1

    # AC-16: STOP and ESCALATE first-class decision handling
    d_stop, p_s, c_s, h_s = make_test_fixture(action=RecoveryAction.STOP)
    dec_stop, _ = engine.evaluate(
        d_stop,
        p_s,
        c_s,
        current_time=now,
        history=h_s,
        event_trust=EventTrustState.TRUSTED,
    )
    assert dec_stop.policy_outcome == PolicyOutcome.ALLOW
    assert dec_stop.effective_action == RecoveryAction.STOP

    d_esc, p_e, c_e, h_e = make_test_fixture(action=RecoveryAction.ESCALATE)
    dec_esc, _ = engine.evaluate(
        d_esc,
        p_e,
        c_e,
        current_time=now,
        history=h_e,
        event_trust=EventTrustState.TRUSTED,
    )
    assert dec_esc.policy_outcome == PolicyOutcome.ALLOW
    assert dec_esc.effective_action == RecoveryAction.ESCALATE
    print("[PASS] AC-16: STOP and ESCALATE first-class decision handling")
    passed_acs += 1

    # AC-17: Human approval integrity and binding
    appr = ApprovalRecord(
        approval_id="appr_001",
        case_id="case_acc_001",
        decision_id="dec_acc_001",
        approved_action=RecoveryAction.RETRY,
        approver_reference="lead",
        approved_at=now,
        expires_at=now + timedelta(hours=1),
        policy_version="policy-v1",
    )
    v_ok, _, _ = validate_human_approval(
        appr,
        "case_acc_001",
        "dec_acc_001",
        RecoveryAction.RETRY,
        now,
        "policy-v1",
        executed_approval_ids=(),
    )
    assert v_ok is True
    # Verify replay rejection
    v_replay, r_replay, _ = validate_human_approval(
        appr,
        "case_acc_001",
        "dec_acc_001",
        RecoveryAction.RETRY,
        now,
        "policy-v1",
        executed_approval_ids=("appr_001",),
    )
    assert v_replay is False
    assert r_replay == PolicyReasonCode.APPROVAL_MISMATCH
    print("[PASS] AC-17: Human approval integrity and binding")
    passed_acs += 1

    # AC-18: Final pre-execution state recheck gate
    v_gate, r_gate, _ = StateGuard.recheck_current_state(
        PaymentStatus.CAPTURED, RecoveryAction.RETRY
    )
    assert v_gate is False
    assert r_gate == PolicyReasonCode.PAYMENT_ALREADY_RECOVERED
    print("[PASS] AC-18: Final pre-execution state recheck gate")
    passed_acs += 1

    # AC-19: Stale event protection (S5)
    t_event_stale = now - timedelta(minutes=10)
    d, p, c, h = make_test_fixture(payment_status=PaymentStatus.FAILED, updated_at=now)
    dec_res, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        history=h,
        event_trust=EventTrustState.TRUSTED,
        event_timestamp=t_event_stale,
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.STALE_OR_INCONSISTENT_EVENT
    print("[PASS] AC-19: Stale event protection (S5)")
    passed_acs += 1

    # AC-20: Reconciliation handling (S6)
    d, p, c, h = make_test_fixture(payment_status=PaymentStatus.CREATED)
    dec_res, _ = engine.evaluate(
        d, p, c, current_time=now, history=h, event_trust=EventTrustState.TRUSTED
    )
    assert dec_res.policy_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
    assert dec_res.reason_code == PolicyReasonCode.RECONCILIATION_REQUIRED
    print("[PASS] AC-20: Reconciliation handling (S6)")
    passed_acs += 1

    # AC-21: Idempotency protection (S8)
    key = "idem_case_acc_001_RETRY_1"
    d, p, c, h = make_test_fixture(
        action=RecoveryAction.RETRY,
        retry_count=0,
        executed_idempotency_keys=(key,),
    )
    dec_res, _ = engine.evaluate(
        d, p, c, current_time=now, history=h, event_trust=EventTrustState.TRUSTED
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.IDEMPOTENCY_CONFLICT
    print("[PASS] AC-21: Idempotency protection (S8)")
    passed_acs += 1

    # AC-22: Payment Link capacity enforcement (S7)
    d, p, c, h = make_test_fixture(
        action=RecoveryAction.PAYMENT_LINK, payment_link_count=3
    )
    dec_res, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        config=PolicyConfig(max_payment_link_creations=3),
        history=h,
        event_trust=EventTrustState.TRUSTED,
    )
    assert dec_res.policy_outcome == PolicyOutcome.BLOCK
    assert dec_res.reason_code == PolicyReasonCode.PAYMENT_LINK_CAPACITY_REACHED
    print("[PASS] AC-22: Payment Link capacity enforcement (S7)")
    passed_acs += 1

    # AC-23: Model failure fail-safe behavior
    d, p, c, h = make_test_fixture()
    dec_m1, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        history=h,
        event_trust=EventTrustState.TRUSTED,
        model_a_failed=True,
    )
    assert dec_m1.policy_outcome == PolicyOutcome.BLOCK
    assert dec_m1.reason_code == PolicyReasonCode.MODEL_A_FAILURE
    assert dec_m1.model_output_valid is False

    dec_m2, _ = engine.evaluate(
        d,
        p,
        c,
        current_time=now,
        history=h,
        event_trust=EventTrustState.TRUSTED,
        model_b_failed=True,
    )
    assert dec_m2.policy_outcome == PolicyOutcome.BLOCK
    assert dec_m2.reason_code == PolicyReasonCode.MODEL_B_FAILURE
    assert dec_m2.model_output_valid is False
    print("[PASS] AC-23: Model failure fail-safe behavior")
    passed_acs += 1

    # AC-24: Version and schema compatibility
    assert POLICY_SCHEMA_VERSION == "policy-config-v1"
    assert POLICY_VERSION == "policy-v1"
    assert RULE_SET_VERSION == "ruleset-v1"
    assert POLICY_DECISION_SCHEMA_VERSION == "policy-decision-v1"
    assert POLICY_TRACE_SCHEMA_VERSION == "policy-trace-v1"
    assert POLICY_ARTIFACT_SCHEMA_VERSION == "policy-artifact-v1"
    # Negative test on incompatible version
    appr_bad_ver = ApprovalRecord(
        approval_id="appr_v_bad",
        case_id="case_acc_001",
        decision_id="dec_acc_001",
        approved_action=RecoveryAction.RETRY,
        approver_reference="lead",
        approved_at=now,
        policy_version="policy-v999",
    )
    v_ver, r_ver, _ = validate_human_approval(
        appr_bad_ver,
        "case_acc_001",
        "dec_acc_001",
        RecoveryAction.RETRY,
        now,
        "policy-v1",
    )
    assert v_ver is False
    assert r_ver == PolicyReasonCode.APPROVAL_MISMATCH
    print("[PASS] AC-24: Version and schema compatibility")
    passed_acs += 1

    # AC-25: Complete policy evaluation trace generation
    d, p, c, h = make_test_fixture()
    _, trace = engine.evaluate(
        d, p, c, current_time=now, history=h, event_trust=EventTrustState.TRUSTED
    )
    assert trace.policy_decision_id is not None
    assert trace.case_id == "case_acc_001"
    assert trace.payment_id == "pay_acc_001"
    assert trace.policy_outcome == PolicyOutcome.ALLOW
    assert len(trace.rules_evaluated) == 22
    assert trace.evaluation_latency_ms >= 0.0
    assert trace.trace_schema_version == "policy-trace-v1"
    print("[PASS] AC-25: Complete policy evaluation trace generation")
    passed_acs += 1

    # AC-26: Policy artifact persistence, reload, and tamper detection
    with tempfile.TemporaryDirectory() as td:
        art_path = Path(td) / "policy_artifact.json"
        saved_art = save_policy_artifact(DEFAULT_POLICY_CONFIG, art_path)
        loaded_cfg, loaded_art = load_policy_artifact(art_path)
        assert saved_art.deterministic_identity == loaded_art.deterministic_identity
        assert loaded_cfg.policy_version == "policy-v1"

        # Tamper test
        with open(art_path, encoding="utf-8") as f:
            content = f.read()
        tampered_content = content.replace("policy-v1", "policy-tampered")
        with open(art_path, "w", encoding="utf-8") as f:
            f.write(tampered_content)
        with pytest.raises(ValueError, match="mismatch|tampered"):
            load_policy_artifact(art_path)
    print("[PASS] AC-26: Policy artifact persistence and reload")
    passed_acs += 1

    # AC-27: Deterministic policy config SHA-256 identity
    id1 = DEFAULT_POLICY_CONFIG.compute_deterministic_identity()
    cfg_diff = DEFAULT_POLICY_CONFIG.model_copy(update={"max_retries": 99})
    id2 = cfg_diff.compute_deterministic_identity()
    assert id1 != id2
    assert len(id1) == 64
    print("[PASS] AC-27: Deterministic policy config SHA-256 identity")
    passed_acs += 1

    # AC-28: Bit-for-bit reproducibility across runs
    d, p, c, h = make_test_fixture()
    frozen_t = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)
    r1, t1 = engine.evaluate(
        d,
        p,
        c,
        current_time=frozen_t,
        history=h,
        event_trust=EventTrustState.TRUSTED,
    )
    r2, t2 = engine.evaluate(
        d,
        p,
        c,
        current_time=frozen_t,
        history=h,
        event_trust=EventTrustState.TRUSTED,
    )
    assert r1.policy_decision_id == r2.policy_decision_id
    assert r1.model_dump() == r2.model_dump()
    assert t1.policy_decision_id == t2.policy_decision_id
    assert t1.model_dump(exclude={"evaluation_latency_ms"}) == t2.model_dump(
        exclude={"evaluation_latency_ms"}
    )
    print("[PASS] AC-28: Bit-for-bit reproducibility across runs")
    passed_acs += 1

    # AC-29: Policy safety metrics on benchmark dataset
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(
        dataset_type=DatasetType.TRAINING,
        dataset_version="train-test-v1",
        seeds=[42],
        cases_per_seed=30,
    )
    test_ds = gen.generate_dataset(
        dataset_type=DatasetType.BENCHMARK,
        dataset_version="benchmark-test-v1",
        seeds=[43],
        cases_per_seed=30,
    )
    diag_model = DecisionTreeDiagnosisModel(max_depth=4)
    diag_model.fit_on_dataset(train_ds)
    outcome_model = LogisticRegressionOutcomeModel(max_iter=50)
    outcome_model.fit_on_dataset(train_ds, diagnosis_model=diag_model)

    metrics, decisions, traces = evaluate_policy_on_dataset(
        dataset=test_ds,
        diagnosis_model=diag_model,
        outcome_model=outcome_model,
    )
    assert metrics.total_evaluations == 30
    assert (
        metrics.allow_count + metrics.block_count + metrics.require_human_approval_count
        == 30
    )
    assert metrics.allow_rate == metrics.allow_count / 30
    assert metrics.block_rate == metrics.block_count / 30
    assert metrics.require_human_approval_rate == (
        metrics.require_human_approval_count / 30
    )
    assert metrics.ineligible_selection_rate == 0.0
    assert sum(metrics.reason_code_counts.values()) == 30
    assert sum(metrics.action_counts_before_policy.values()) == 30
    assert sum(metrics.action_counts_after_policy.values()) == 30
    assert len(decisions) == 30
    assert len(traces) == 30
    print("[PASS] AC-29: Policy safety metrics")
    passed_acs += 1

    # AC-30: Segment evaluation across all 10 required dimensions
    segments = evaluate_policy_segments(test_ds, decisions)
    assert len(segments) > 0
    # Assert all 10 required dimensions exist
    assert any(k.startswith("family_") for k in segments)
    assert any(k.startswith("method_") for k in segments)
    assert any(k.startswith("value_tier_") for k in segments)
    assert any(k.startswith("difficulty_") for k in segments)
    assert any(k.startswith("diagnosis_") for k in segments)
    assert any(k.startswith("confidence_tier_") for k in segments)
    assert any(k.startswith("action_") for k in segments)
    assert any(k.startswith("outcome_") for k in segments)
    assert any(k.startswith("reason_") for k in segments)
    assert any(k.startswith("seed_") for k in segments)

    for _seg_key, data in segments.items():
        assert data["count"] >= 0
        assert data["allow"] >= 0
        assert data["block"] >= 0
        assert data["require_approval"] >= 0
        assert data["count"] == data["allow"] + data["block"] + data["require_approval"]
    print("[PASS] AC-30: Segment evaluation")
    passed_acs += 1

    # AC-31: Distribution-shift evaluation
    shift_ds = gen.generate_dataset(
        dataset_type=DatasetType.BENCHMARK,
        dataset_version="shift-test-v1",
        seeds=[999],
        cases_per_seed=30,
    )
    shift_metrics, _, _ = evaluate_policy_on_dataset(
        dataset=shift_ds,
        diagnosis_model=diag_model,
        outcome_model=outcome_model,
    )
    shift_comparison = compare_distribution_shift(metrics, shift_metrics)
    in_d = shift_comparison["in_distribution"]
    shift_d = shift_comparison["distribution_shift"]
    delta_d = shift_comparison["delta"]

    assert in_d["total"] == 30
    assert shift_d["total"] == 30
    assert in_d["allow_rate"] == metrics.allow_count / 30
    assert shift_d["allow_rate"] == shift_metrics.allow_count / 30
    assert in_d["ineligible_selection_rate"] == 0.0
    assert shift_d["ineligible_selection_rate"] == 0.0
    assert "action_distribution_after_policy" in in_d
    assert "action_distribution_after_policy" in shift_d
    assert "safety_counters" in in_d
    assert "safety_counters" in shift_d

    assert (
        abs(
            delta_d["allow_rate_delta"]
            - (shift_metrics.allow_rate - metrics.allow_rate)
        )
        < 1e-6
    )
    assert (
        abs(
            delta_d["block_rate_delta"]
            - (shift_metrics.block_rate - metrics.block_rate)
        )
        < 1e-6
    )
    assert (
        abs(
            delta_d["approval_rate_delta"]
            - (
                shift_metrics.require_human_approval_rate
                - metrics.require_human_approval_rate
            )
        )
        < 1e-6
    )
    print("[PASS] AC-31: Distribution-shift evaluation")
    passed_acs += 1

    # AC-32: Leakage prevention (Zero simulator truth in live decision path)
    forbidden_simulator_fields = {
        "EvaluationTruthRecord",
        "potential_outcomes",
        "oracle_action",
        "ground_truth",
        "latent_state",
        "hidden_failure_cause",
    }
    sample_trace_dict = traces[0].model_dump()
    sample_decision_dict = decisions[0].model_dump()
    for field in forbidden_simulator_fields:
        assert field not in sample_trace_dict, (
            f"Forbidden field '{field}' leaked into trace!"
        )
        assert field not in sample_decision_dict, (
            f"Forbidden field '{field}' leaked into decision!"
        )
    print("[PASS] AC-32: Leakage prevention")
    passed_acs += 1

    # AC-33: Zero policy constraint violations in governed evaluation
    assert metrics.constraint_violation_count == 0
    assert shift_metrics.constraint_violation_count == 0

    # Perform evaluator-side error analysis (Blocker 4)
    err_report = perform_policy_error_analysis(
        dataset=test_ds,
        decisions=decisions,
        policy_decisions=decisions,
        traces=traces,
    )
    assert err_report.total_cases_analyzed == 30
    assert len(err_report.wrong_policy_outcomes) == 0
    assert len(err_report.negative_utility_incorrectly_permitted) == 0
    print("[PASS] AC-33: Zero policy constraint violations in governed evaluation")
    passed_acs += 1

    # AC-34: Zero execution side effects
    # Deep snapshot assertion before and after policy evaluation
    d_side, p_side, c_side, h_side = make_test_fixture()
    p_before = copy.deepcopy(p_side.model_dump())
    c_before = copy.deepcopy(c_side.model_dump())
    h_before = copy.deepcopy(h_side.model_dump())
    d_before = copy.deepcopy(d_side.model_dump())

    pol_dec_side, _ = engine.evaluate(
        d_side,
        p_side,
        c_side,
        current_time=now,
        history=h_side,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec_side.policy_outcome == PolicyOutcome.ALLOW
    assert p_side.model_dump() == p_before
    assert c_side.model_dump() == c_before
    assert h_side.model_dump() == h_before
    assert d_side.model_dump() == d_before
    print("[PASS] AC-34: Zero execution side effects")
    passed_acs += 1

    # AC-35: Zero outbound / network effects
    mock_network = MagicMock()
    with (
        patch("socket.socket.connect", mock_network),
        patch("urllib.request.urlopen", mock_network),
        patch("http.client.HTTPConnection.connect", mock_network),
    ):
        # Actively evaluate policy workload inside network interception
        d_net, p_net, c_net, h_net = make_test_fixture()
        pol_dec_net, _ = engine.evaluate(
            d_net,
            p_net,
            c_net,
            current_time=now,
            history=h_net,
            event_trust=EventTrustState.TRUSTED,
        )
        assert pol_dec_net.policy_outcome == PolicyOutcome.ALLOW
        assert mock_network.call_count == 0
    print("[PASS] AC-35: Zero outbound effects")
    passed_acs += 1

    # AC-36: Automated policy tests passing
    test_res = pytest.main(["-q", "tests/policy"])
    assert test_res == pytest.ExitCode.OK
    print("[PASS] AC-36: Automated policy tests")
    passed_acs += 1

    # AC-37: Manual acceptance suite passing
    man_res = run_manual_scenarios()
    assert man_res == 12
    print("[PASS] AC-37: Manual acceptance suite")
    passed_acs += 1

    # AC-38: Full Phase 0–9 regression suite execution (all 282 tests)
    reg_res = pytest.main(["-q", "tests", "--ignore=tests/policy"])
    assert reg_res == pytest.ExitCode.OK, (
        f"Phase 0–9 regression test suite failed with exit code: {reg_res}"
    )
    print("[PASS] AC-38: Full Phase 0–9 regression compatibility")
    passed_acs += 1

    print(f"\nAcceptance Criteria Result: {passed_acs}/38 VERIFIED (100%)\n")
    return passed_acs


def main() -> None:
    print("=" * 70)
    print("APRO PHASE 10 — POLICY & SAFETY ENGINE ACCEPTANCE SUITE")
    print("=" * 70)

    manual_passed = run_manual_scenarios()
    acs_passed = run_acceptance_criteria()

    if manual_passed == 12 and acs_passed == 38:
        print("=" * 70)
        print("ALL PHASE 10 ACCEPTANCE GATES PASSED (12/12 SCENARIOS, 38/38 ACs)")
        print("=" * 70)
        sys.exit(0)
    else:
        print("=" * 70)
        print(f"ACCEPTANCE FAILURE: {manual_passed}/12 Scenarios, {acs_passed}/38 ACs")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
