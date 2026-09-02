"""Unit tests for Phase 10 PolicyEngine evaluation, precedence, side effects,
network isolation, and model validity semantics.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from apro.decision.enums import DecisionStatus
from apro.decision.models import ActionEligibility, ActionUtility, RecoveryDecision
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Payment, RecoveryCase
from apro.policy.config import PolicyConfig
from apro.policy.engine import PolicyEngine
from apro.policy.enums import PolicyOutcome, PolicyReasonCode
from apro.policy.models import ActionExecutionHistory, ApprovalRecord, EventTrustState
from apro.recovery_prediction.enums import RecoveryAction


def make_engine_inputs(
    case_id: str = "case_001",
    payment_id: str = "pay_001",
    action: RecoveryAction = RecoveryAction.RETRY,
    payment_status: PaymentStatus = PaymentStatus.FAILED,
    payment_amount: int = 50000,
    confidence: float = 0.85,
    erv: int = 4000,
    retry_count: int = 0,
    last_retry_at: datetime | None = None,
    total_interventions: int = 0,
    executed_approval_ids: tuple[str, ...] = (),
) -> tuple[RecoveryDecision, Payment, RecoveryCase, ActionExecutionHistory]:
    now = datetime.now(UTC)
    payment = Payment(
        payment_id=payment_id,
        customer_id="cust_001",
        provider="razorpay",
        amount=payment_amount,
        currency="INR",
        method="card",
        status=payment_status,
        created_at=now,
        updated_at=now,
        captured_at=now if payment_status == PaymentStatus.CAPTURED else None,
    )
    case = RecoveryCase(
        case_id=case_id,
        payment_id=payment_id,
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
        recovery_case_id=case_id,
        selected_action=action,
        decision_status=DecisionStatus.ACTION_SELECTED,
        expected_recovery_value=erv,
        utility_by_action=utilities,
        eligibility_by_action=eligibilities,
        decision_confidence=confidence,
        rationale="Engine test decision",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        dataset_version="dataset-v1",
    )
    history = ActionExecutionHistory(
        retry_count=retry_count,
        last_retry_at=last_retry_at,
        total_interventions=total_interventions,
        executed_approval_ids=executed_approval_ids,
    )
    return decision, payment, case, history


def test_engine_allow_path():
    """Verify normal compliant decision evaluates to ALLOW."""
    engine = PolicyEngine()
    decision, payment, case, history = make_engine_inputs()
    now = datetime.now(UTC)

    pol_dec, trace = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        history=history,
        event_trust=EventTrustState.TRUSTED,
    )

    assert pol_dec.policy_outcome == PolicyOutcome.ALLOW
    assert pol_dec.effective_action == RecoveryAction.RETRY
    assert pol_dec.reason_code == PolicyReasonCode.POLICY_ALLOWED
    assert pol_dec.approval_required is False
    assert pol_dec.model_output_valid is True


def test_engine_missing_current_time_raises_error():
    """Verify missing current_time raises explicit ValueError."""
    engine = PolicyEngine()
    decision, payment, case, history = make_engine_inputs()

    with pytest.raises(ValueError, match="Explicit current_time must be provided"):
        engine.evaluate(
            decision,
            payment,
            case,
            current_time=None,  # type: ignore[arg-type]
            history=history,
            event_trust=EventTrustState.TRUSTED,
        )


def test_engine_zero_execution_side_effects():
    """Verify PolicyEngine.evaluate performs zero side-effects
    and mutates zero entities.
    """
    engine = PolicyEngine()
    decision, payment, case, history = make_engine_inputs()
    now = datetime.now(UTC)

    # Capture snapshot before evaluation
    payment_before = payment.model_dump()
    case_before = case.model_dump()
    history_before = history.model_dump()
    decision_before = decision.model_dump()

    pol_dec, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        history=history,
        event_trust=EventTrustState.TRUSTED,
    )

    assert pol_dec.policy_outcome == PolicyOutcome.ALLOW
    # Verify exact equality of before and after states
    assert payment.model_dump() == payment_before
    assert case.model_dump() == case_before
    assert history.model_dump() == history_before
    assert decision.model_dump() == decision_before
    # Action counters untouched
    assert history.retry_count == 0
    assert history.total_interventions == 0


def test_engine_zero_network_effects():
    """Verify PolicyEngine evaluation executes zero outbound socket
    or HTTP network calls.
    """
    engine = PolicyEngine()
    decision, payment, case, history = make_engine_inputs()
    now = datetime.now(UTC)

    mock_connect = MagicMock()
    with (
        patch("socket.socket.connect", mock_connect),
        patch("urllib.request.urlopen", mock_connect),
        patch("http.client.HTTPConnection.connect", mock_connect),
    ):
        pol_dec, _ = engine.evaluate(
            decision,
            payment,
            case,
            current_time=now,
            history=history,
            event_trust=EventTrustState.TRUSTED,
        )
        assert pol_dec.policy_outcome == PolicyOutcome.ALLOW
        assert mock_connect.call_count == 0


def test_engine_model_output_valid_semantics():
    """Verify model_output_valid is False when M1, M2, H5 or entity binding fails."""
    engine = PolicyEngine()
    decision, payment, case, history = make_engine_inputs()
    now = datetime.now(UTC)

    # 1. Normal valid output
    dec_ok, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        history=history,
        event_trust=EventTrustState.TRUSTED,
    )
    assert dec_ok.model_output_valid is True

    # 2. Model A failure
    dec_m1, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        history=history,
        event_trust=EventTrustState.TRUSTED,
        model_a_failed=True,
    )
    assert dec_m1.model_output_valid is False

    # 3. Model B failure
    dec_m2, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        history=history,
        event_trust=EventTrustState.TRUSTED,
        model_b_failed=True,
    )
    assert dec_m2.model_output_valid is False


def test_engine_untrusted_event_fails_closed():
    """Verify missing/untrusted event fails closed to BLOCK."""
    engine = PolicyEngine()
    decision, payment, case, history = make_engine_inputs()
    now = datetime.now(UTC)

    pol_dec, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        history=history,
        event_trust=None,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.INVALID_EVENT


def test_engine_entity_binding_mismatch_blocks():
    """Verify mismatched payment/case IDs fail closed."""
    engine = PolicyEngine()
    now = datetime.now(UTC)
    payment = Payment(
        payment_id="pay_001",
        customer_id="cust_001",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=PaymentStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    case = RecoveryCase(
        case_id="case_001",
        payment_id="pay_DIFFERENT",  # Mismatch!
        customer_id="cust_001",
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
    )
    decision = make_engine_inputs(case_id="case_001")[0]

    pol_dec, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.INVALID_MODEL_OUTPUT
    assert pol_dec.model_output_valid is False


def test_engine_model_failure_fallback_blocks():
    """Verify Model A or Model B failure results in fail-closed BLOCK."""
    engine = PolicyEngine()
    decision, payment, case, history = make_engine_inputs()
    now = datetime.now(UTC)

    pol_dec_a, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        history=history,
        event_trust=EventTrustState.TRUSTED,
        model_a_failed=True,
    )
    assert pol_dec_a.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec_a.reason_code == PolicyReasonCode.MODEL_A_FAILURE

    pol_dec_b, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        history=history,
        event_trust=EventTrustState.TRUSTED,
        model_b_failed=True,
    )
    assert pol_dec_b.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec_b.reason_code == PolicyReasonCode.MODEL_B_FAILURE


def test_engine_captured_payment_blocks():
    """Verify captured payment unconditionally produces BLOCK."""
    engine = PolicyEngine()
    decision, payment, case, history = make_engine_inputs(
        payment_status=PaymentStatus.CAPTURED
    )
    now = datetime.now(UTC)

    pol_dec, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        history=history,
        event_trust=EventTrustState.TRUSTED,
    )

    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.effective_action is None
    assert pol_dec.reason_code == PolicyReasonCode.PAYMENT_ALREADY_RECOVERED


def test_engine_high_value_requires_approval_then_allows_with_approval():
    """Verify high value produces REQUIRE_HUMAN_APPROVAL without token,
    and ALLOW with valid token.
    """
    engine = PolicyEngine()
    cfg = PolicyConfig(high_value_threshold=100000)
    decision, payment, case, history = make_engine_inputs(payment_amount=150000)
    now = datetime.now(UTC)

    # 1. Without approval token
    pol_dec_no_appr, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        config=cfg,
        history=history,
        event_trust=EventTrustState.TRUSTED,
    )
    assert pol_dec_no_appr.policy_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
    assert pol_dec_no_appr.reason_code == PolicyReasonCode.HIGH_VALUE_REQUIRES_APPROVAL
    assert pol_dec_no_appr.approval_required is True
    assert pol_dec_no_appr.effective_action is None

    # 2. With matching valid approval token
    valid_appr = ApprovalRecord(
        approval_id="appr_hv_01",
        case_id="case_001",
        decision_id="dec_001",
        approved_action=RecoveryAction.RETRY,
        approver_reference="risk_lead_01",
        approved_at=now,
        expires_at=now + timedelta(hours=24),
        policy_version=cfg.policy_version,
    )
    pol_dec_approved, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        config=cfg,
        history=history,
        event_trust=EventTrustState.TRUSTED,
        approval=valid_appr,
    )
    assert pol_dec_approved.policy_outcome == PolicyOutcome.ALLOW
    assert pol_dec_approved.effective_action == RecoveryAction.RETRY
    assert pol_dec_approved.approval_reference == "appr_hv_01"


def test_engine_replayed_approval_blocks():
    """Verify replaying an already consumed approval produces BLOCK."""
    engine = PolicyEngine()
    cfg = PolicyConfig(high_value_threshold=100000)
    now = datetime.now(UTC)
    decision, payment, case, history = make_engine_inputs(
        payment_amount=150000,
        executed_approval_ids=("appr_hv_01",),
    )
    replayed_appr = ApprovalRecord(
        approval_id="appr_hv_01",
        case_id="case_001",
        decision_id="dec_001",
        approved_action=RecoveryAction.RETRY,
        approver_reference="risk_lead_01",
        approved_at=now,
        expires_at=now + timedelta(hours=24),
        policy_version=cfg.policy_version,
    )
    pol_dec, _ = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        config=cfg,
        history=history,
        event_trust=EventTrustState.TRUSTED,
        approval=replayed_appr,
    )
    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.APPROVAL_MISMATCH


def test_engine_hard_block_overrides_high_value_approval():
    """Verify hard block (captured payment) outranks human approval requirement."""
    engine = PolicyEngine()
    cfg = PolicyConfig(high_value_threshold=100000)
    decision, payment, case, history = make_engine_inputs(
        payment_status=PaymentStatus.CAPTURED,
        payment_amount=150000,
    )
    now = datetime.now(UTC)

    pol_dec, trace = engine.evaluate(
        decision,
        payment,
        case,
        current_time=now,
        config=cfg,
        history=history,
        event_trust=EventTrustState.TRUSTED,
    )

    assert pol_dec.policy_outcome == PolicyOutcome.BLOCK
    assert pol_dec.reason_code == PolicyReasonCode.PAYMENT_ALREADY_RECOVERED
    assert "H1_PAYMENT_CAPTURED" in pol_dec.rules_triggered
    assert "S1_HIGH_VALUE" in pol_dec.rules_triggered
