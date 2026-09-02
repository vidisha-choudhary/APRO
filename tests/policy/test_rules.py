"""Unit tests for individual policy rules and trigger logic
(H1–H5, M1–M2, R1–R4, S1–S8, A1–A3).
"""

from datetime import UTC, datetime, timedelta

from apro.decision.enums import DecisionStatus
from apro.decision.models import ActionEligibility, ActionUtility, RecoveryDecision
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Payment, RecoveryCase
from apro.policy.config import DEFAULT_POLICY_CONFIG, PolicyConfig
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import ActionExecutionHistory, ApprovalRecord, EventTrustState
from apro.policy.rules import (
    PolicyRuleContext,
    eval_a1_approval_required,
    eval_a2_approval_mismatch,
    eval_a3_approval_expired,
    eval_h1_payment_captured,
    eval_h2_invalid_event,
    eval_h3_duplicate_event,
    eval_h4_unsupported_action,
    eval_h5_invalid_model_output,
    eval_m1_model_a_failure,
    eval_m2_model_b_failure,
    eval_r1_retry_limit,
    eval_r2_retry_cooldown,
    eval_r3_same_action_limit,
    eval_r4_total_intervention_limit,
    eval_s1_high_value,
    eval_s2_low_confidence,
    eval_s3_min_erv,
    eval_s4_negative_erv,
    eval_s5_stale_state,
    eval_s6_reconciliation,
    eval_s7_payment_link_capacity,
    eval_s8_idempotency_conflict,
)
from apro.recovery_prediction.enums import RecoveryAction


def make_context(
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
    event_trust: EventTrustState = EventTrustState.TRUSTED,
    is_duplicate_event: bool = False,
    event_timestamp: datetime | None = None,
    approval: ApprovalRecord | None = None,
    idempotency_key: str | None = None,
    executed_keys: tuple[str, ...] = (),
    executed_approval_ids: tuple[str, ...] = (),
    model_a_failed: bool = False,
    model_b_failed: bool = False,
    config: PolicyConfig = DEFAULT_POLICY_CONFIG,
    payment_updated_at: datetime | None = None,
) -> PolicyRuleContext:
    now = datetime.now(UTC)
    updated = payment_updated_at or now
    payment = Payment(
        payment_id="pay_001",
        customer_id="cust_001",
        provider="razorpay",
        amount=payment_amount,
        currency="INR",
        method="card",
        status=payment_status,
        created_at=now,
        updated_at=updated,
        captured_at=now if payment_status == PaymentStatus.CAPTURED else None,
    )
    case = RecoveryCase(
        case_id="case_001",
        payment_id="pay_001",
        customer_id="cust_001",
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
        decision_id="dec_001",
        record_id="rec_001",
        scenario_id="scen_001",
        recovery_case_id="case_001",
        selected_action=action,
        decision_status=DecisionStatus.ACTION_SELECTED,
        expected_recovery_value=erv,
        utility_by_action=utilities,
        eligibility_by_action=eligibilities,
        decision_confidence=confidence,
        rationale="Rule test decision",
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
        executed_idempotency_keys=executed_keys,
        executed_approval_ids=executed_approval_ids,
    )
    return PolicyRuleContext(
        decision=decision,
        payment=payment,
        case=case,
        config=config,
        history=history,
        event_trust=event_trust,
        is_duplicate_event=is_duplicate_event,
        event_timestamp=event_timestamp,
        approval=approval,
        current_time=now,
        idempotency_key=idempotency_key,
        model_a_failed=model_a_failed,
        model_b_failed=model_b_failed,
    )


def test_eval_h1_captured_payment():
    """H1: Captured payment triggers PAYMENT_ALREADY_RECOVERED."""
    ctx_cap = make_context(payment_status=PaymentStatus.CAPTURED)
    res = eval_h1_payment_captured(ctx_cap)
    assert res.triggered is True
    assert res.outcome == PolicyOutcome.BLOCK
    assert res.reason_code == PolicyReasonCode.PAYMENT_ALREADY_RECOVERED


def test_eval_h2_invalid_event():
    """H2: Untrusted event triggers INVALID_EVENT."""
    ctx_untrust = make_context(event_trust=EventTrustState.UNTRUSTED)
    res = eval_h2_invalid_event(ctx_untrust)
    assert res.triggered is True
    assert res.outcome == PolicyOutcome.BLOCK
    assert res.reason_code == PolicyReasonCode.INVALID_EVENT


def test_eval_h3_duplicate_event():
    """H3: Duplicate event triggers DUPLICATE_EVENT."""
    ctx_dup = make_context(is_duplicate_event=True)
    res = eval_h3_duplicate_event(ctx_dup)
    assert res.triggered is True
    assert res.reason_code == PolicyReasonCode.DUPLICATE_EVENT


def test_eval_h4_unsupported_action():
    """H4: Valid supported action does not trigger."""
    ctx_valid = make_context(action=RecoveryAction.RETRY)
    res = eval_h4_unsupported_action(ctx_valid)
    assert res.triggered is False


def test_eval_h5_invalid_model_output():
    """H5: Valid model output does not trigger."""
    ctx_valid = make_context()
    res = eval_h5_invalid_model_output(ctx_valid)
    assert res.triggered is False


def test_eval_m1_model_a_failure():
    """M1: Diagnosis Model A failure triggers MODEL_A_FAILURE."""
    ctx_fail = make_context(model_a_failed=True)
    res = eval_m1_model_a_failure(ctx_fail)
    assert res.triggered is True
    assert res.outcome == PolicyOutcome.BLOCK
    assert res.reason_code == PolicyReasonCode.MODEL_A_FAILURE


def test_eval_m2_model_b_failure():
    """M2: Outcome Model B failure triggers MODEL_B_FAILURE."""
    ctx_fail = make_context(model_b_failed=True)
    res = eval_m2_model_b_failure(ctx_fail)
    assert res.triggered is True
    assert res.outcome == PolicyOutcome.BLOCK
    assert res.reason_code == PolicyReasonCode.MODEL_B_FAILURE


def test_eval_r1_retry_limit():
    """R1: Retry count >= limit triggers MAX_RETRIES_REACHED."""
    ctx_lim = make_context(
        action=RecoveryAction.RETRY,
        retry_count=3,
        config=PolicyConfig(max_retries=3),
    )
    res = eval_r1_retry_limit(ctx_lim)
    assert res.triggered is True
    assert res.reason_code == PolicyReasonCode.MAX_RETRIES_REACHED


def test_eval_r2_retry_cooldown():
    """R2: Elapsed time < cooldown triggers RETRY_COOLDOWN_ACTIVE."""
    now = datetime.now(UTC)
    last_retry = now - timedelta(seconds=60)
    ctx_cd = make_context(
        action=RecoveryAction.RETRY,
        last_retry_at=last_retry,
        config=PolicyConfig(retry_cooldown_seconds=300),
    )
    res = eval_r2_retry_cooldown(ctx_cd)
    assert res.triggered is True
    assert res.reason_code == PolicyReasonCode.RETRY_COOLDOWN_ACTIVE


def test_eval_r3_same_action_limit():
    """R3: Same action repeated >= limit triggers
    MAX_SAME_ACTION_REPETITIONS_REACHED.
    """
    ctx_same = make_context(
        action=RecoveryAction.PAYMENT_LINK,
        last_action=RecoveryAction.PAYMENT_LINK,
        same_action_count=2,
        config=PolicyConfig(max_same_action_repetitions=2),
    )
    res = eval_r3_same_action_limit(ctx_same)
    assert res.triggered is True
    assert res.reason_code == PolicyReasonCode.MAX_SAME_ACTION_REPETITIONS_REACHED


def test_eval_r4_total_interventions():
    """R4: Total interventions >= limit triggers
    MAX_TOTAL_INTERVENTIONS_REACHED.
    """
    ctx_total = make_context(
        action=RecoveryAction.OUTREACH,
        total_interventions=4,
        config=PolicyConfig(max_total_interventions=4),
    )
    res = eval_r4_total_intervention_limit(ctx_total)
    assert res.triggered is True
    assert res.reason_code == PolicyReasonCode.MAX_TOTAL_INTERVENTIONS_REACHED


def test_eval_s1_high_value():
    """S1: High value amount triggers REQUIRE_HUMAN_APPROVAL."""
    ctx_hv = make_context(
        payment_amount=150000, config=PolicyConfig(high_value_threshold=100000)
    )
    res = eval_s1_high_value(ctx_hv)
    assert res.triggered is True
    assert res.outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
    assert res.reason_code == PolicyReasonCode.HIGH_VALUE_REQUIRES_APPROVAL


def test_eval_s2_low_confidence():
    """S2: Low confidence triggers REQUIRE_HUMAN_APPROVAL."""
    ctx_lc = make_context(
        confidence=0.35, config=PolicyConfig(min_decision_confidence=0.50)
    )
    res = eval_s2_low_confidence(ctx_lc)
    assert res.triggered is True
    assert res.reason_code == PolicyReasonCode.LOW_CONFIDENCE_REQUIRES_APPROVAL


def test_eval_s3_min_erv():
    """S3: ERV below minimum triggers INSUFFICIENT_EXPECTED_VALUE."""
    ctx_erv = make_context(erv=50, config=PolicyConfig(min_expected_recovery_value=100))
    res = eval_s3_min_erv(ctx_erv)
    assert res.triggered is True
    assert res.reason_code == PolicyReasonCode.INSUFFICIENT_EXPECTED_VALUE


def test_eval_s4_negative_erv():
    """S4: Non-positive ERV triggers NEGATIVE_EXPECTED_VALUE."""
    ctx_neg = make_context(erv=0)
    res = eval_s4_negative_erv(ctx_neg)
    assert res.triggered is True
    assert res.reason_code == PolicyReasonCode.NEGATIVE_EXPECTED_VALUE


def test_eval_s5_stale_state():
    """S5: Event older than payment state triggers STALE_OR_INCONSISTENT_EVENT."""
    now = datetime.now(UTC)
    t_event_old = now - timedelta(minutes=5)
    ctx_stale = make_context(
        payment_updated_at=now,
        event_timestamp=t_event_old,
    )
    res = eval_s5_stale_state(ctx_stale)
    assert res.triggered is True
    assert res.reason_code == PolicyReasonCode.STALE_OR_INCONSISTENT_EVENT


def test_eval_s6_reconciliation():
    """S6: Ambiguous payment state triggers RECONCILIATION_REQUIRED."""
    ctx_rec = make_context(payment_status=PaymentStatus.CREATED)
    res = eval_s6_reconciliation(ctx_rec)
    assert res.triggered is True
    assert res.outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
    assert res.reason_code == PolicyReasonCode.RECONCILIATION_REQUIRED


def test_eval_s7_payment_link_capacity():
    """S7: Payment Link capacity limit triggers
    PAYMENT_LINK_CAPACITY_REACHED.
    """
    ctx_link = make_context(
        action=RecoveryAction.PAYMENT_LINK,
        payment_link_count=2,
        config=PolicyConfig(max_payment_link_creations=2),
    )
    res = eval_s7_payment_link_capacity(ctx_link)
    assert res.triggered is True
    assert res.reason_code == PolicyReasonCode.PAYMENT_LINK_CAPACITY_REACHED


def test_eval_s8_idempotency_conflict():
    """S8: Executed idempotency key triggers IDEMPOTENCY_CONFLICT."""
    key = "idem_case_001_RETRY_1"
    ctx_idem = make_context(idempotency_key=key, executed_keys=(key,))
    res = eval_s8_idempotency_conflict(ctx_idem)
    assert res.triggered is True
    assert res.reason_code == PolicyReasonCode.IDEMPOTENCY_CONFLICT


def test_eval_a1_approval_required():
    """A1: Required human approval without token triggers APPROVAL_REQUIRED."""
    ctx_a1 = make_context(
        payment_amount=150000,
        config=PolicyConfig(high_value_threshold=100000),
        approval=None,
    )
    res = eval_a1_approval_required(ctx_a1)
    assert res.triggered is True
    assert res.outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
    assert res.reason_code == PolicyReasonCode.APPROVAL_REQUIRED


def test_eval_a2_approval_mismatch():
    """A2: Mismatched approval triggers APPROVAL_MISMATCH block."""
    now = datetime.now(UTC)
    mismatched_appr = ApprovalRecord(
        approval_id="appr_001",
        case_id="case_other",
        decision_id="dec_001",
        approved_action=RecoveryAction.RETRY,
        approver_reference="lead",
        approved_at=now,
        policy_version="policy-v1",
    )
    ctx_a2 = make_context(approval=mismatched_appr)
    res = eval_a2_approval_mismatch(ctx_a2)
    assert res.triggered is True
    assert res.outcome == PolicyOutcome.BLOCK
    assert res.reason_code == PolicyReasonCode.APPROVAL_MISMATCH


def test_eval_a3_approval_expired():
    """A3: Expired approval triggers APPROVAL_EXPIRED block."""
    now = datetime.now(UTC)
    expired_appr = ApprovalRecord(
        approval_id="appr_001",
        case_id="case_001",
        decision_id="dec_001",
        approved_action=RecoveryAction.RETRY,
        approver_reference="lead",
        approved_at=now - timedelta(days=2),
        expires_at=now - timedelta(days=1),
        policy_version="policy-v1",
    )
    ctx_a3 = make_context(approval=expired_appr)
    res = eval_a3_approval_expired(ctx_a3)
    assert res.triggered is True
    assert res.outcome == PolicyOutcome.BLOCK
    assert res.reason_code == PolicyReasonCode.APPROVAL_EXPIRED
