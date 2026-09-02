"""Unit tests for Phase 10 input validation and fail-closed integrity checks."""

from datetime import UTC, datetime

from apro.decision.enums import DecisionStatus
from apro.decision.models import ActionEligibility, ActionUtility, RecoveryDecision
from apro.domain.enums import PaymentStatus, RecoveryCaseStatus
from apro.domain.models import Payment, RecoveryCase
from apro.policy.models import EventTrustState
from apro.policy.validation import (
    is_action_supported,
    is_valid_currency_amount,
    is_valid_probability,
    validate_entity_binding,
    validate_event_trust,
    validate_recovery_decision_model_output,
)
from apro.recovery_prediction.enums import RecoveryAction


def make_test_payment(
    payment_id: str = "pay_test_001",
    amount: int = 50000,
    status: PaymentStatus = PaymentStatus.FAILED,
) -> Payment:
    now = datetime.now(UTC)
    return Payment(
        payment_id=payment_id,
        customer_id="cust_001",
        provider="razorpay",
        amount=amount,
        currency="INR",
        method="card",
        status=status,
        created_at=now,
        updated_at=now,
    )


def make_test_case(
    case_id: str = "case_001",
    payment_id: str = "pay_test_001",
) -> RecoveryCase:
    now = datetime.now(UTC)
    return RecoveryCase(
        case_id=case_id,
        payment_id=payment_id,
        customer_id="cust_001",
        status=RecoveryCaseStatus.NEW,
        opened_at=now,
        updated_at=now,
    )


def make_test_decision(
    case_id: str = "case_001",
    selected_action: RecoveryAction = RecoveryAction.RETRY,
    confidence: float = 0.85,
    prob: float = 0.70,
    rec_amt: int = 50000,
) -> RecoveryDecision:
    utilities = {
        act: ActionUtility(
            action=act,
            eligible=True,
            predicted_success_probability=prob,
            predicted_recovered_amount=rec_amt,
            expected_gross_recovery=int(prob * rec_amt),
            action_cost=150,
            operational_cost=50,
            customer_friction_cost=0,
            risk_penalty=0,
            expected_recovery_value=int(prob * rec_amt) - 200,
        )
        for act in RecoveryAction
    }
    eligibilities = {
        act: ActionEligibility(action=act, is_eligible=True) for act in RecoveryAction
    }
    return RecoveryDecision(
        decision_id="dec_001",
        record_id="rec_001",
        scenario_id="scen_001",
        recovery_case_id=case_id,
        selected_action=selected_action,
        decision_status=DecisionStatus.ACTION_SELECTED,
        expected_recovery_value=utilities[selected_action].expected_recovery_value,
        utility_by_action=utilities,
        eligibility_by_action=eligibilities,
        decision_confidence=confidence,
        rationale="Test decision",
        diagnosis_model_version="diag-v1",
        outcome_model_version="outcome-v1",
        dataset_version="dataset-v1",
    )


def test_is_valid_probability():
    """Verify probability validator bounds and nan/inf rejection."""
    assert is_valid_probability(0.0) is True
    assert is_valid_probability(1.0) is True
    assert is_valid_probability(0.5) is True
    assert is_valid_probability(-0.01) is False
    assert is_valid_probability(1.01) is False
    assert is_valid_probability(float("nan")) is False
    assert is_valid_probability(float("inf")) is False
    assert is_valid_probability("0.5") is False
    assert is_valid_probability(True) is False


def test_is_valid_currency_amount():
    """Verify monetary amount checks."""
    assert is_valid_currency_amount(0) is True
    assert is_valid_currency_amount(50000) is True
    assert is_valid_currency_amount(-1) is False
    assert is_valid_currency_amount(50001, max_allowed=50000) is False
    assert is_valid_currency_amount(True) is False


def test_validate_entity_binding_success():
    """Verify matching payment, case, and decision binding passes."""
    payment = make_test_payment(payment_id="pay_001")
    case = make_test_case(case_id="case_001", payment_id="pay_001")
    decision = make_test_decision(case_id="case_001")
    valid, err = validate_entity_binding(payment, case, decision)
    assert valid is True
    assert err is None


def test_validate_entity_binding_payment_mismatch():
    """Verify mismatched payment_id is rejected."""
    payment = make_test_payment(payment_id="pay_mismatch")
    case = make_test_case(case_id="case_001", payment_id="pay_001")
    decision = make_test_decision(case_id="case_001")
    valid, err = validate_entity_binding(payment, case, decision)
    assert valid is False
    assert "Payment ID" in str(err)


def test_validate_entity_binding_case_mismatch():
    """Verify mismatched case_id is rejected."""
    payment = make_test_payment(payment_id="pay_001")
    case = make_test_case(case_id="case_001", payment_id="pay_001")
    decision = make_test_decision(case_id="case_different")
    valid, err = validate_entity_binding(payment, case, decision)
    assert valid is False
    assert "Case ID" in str(err)


def test_validate_decision_valid():
    """Verify valid decision passes validation."""
    payment = make_test_payment()
    decision = make_test_decision(rec_amt=50000)
    valid, err = validate_recovery_decision_model_output(decision, payment)
    assert valid is True
    assert err is None


def test_validate_decision_invalid_recovered_amount():
    """Verify recovered amount exceeding payment amount is rejected."""
    payment = make_test_payment(amount=50000)
    decision = make_test_decision(rec_amt=60000)
    valid, err = validate_recovery_decision_model_output(decision, payment)
    assert valid is False
    assert "exceeds payment amount" in str(err)


def test_validate_event_trust():
    """Verify trust validation across boolean, enum, and string formats."""
    assert validate_event_trust(True) is True
    assert validate_event_trust(False) is False
    assert validate_event_trust(None) is False
    assert validate_event_trust(EventTrustState.TRUSTED) is True
    assert validate_event_trust(EventTrustState.UNTRUSTED) is False
    assert validate_event_trust(EventTrustState.UNKNOWN) is False
    assert validate_event_trust("TRUSTED") is True
    assert validate_event_trust("UNTRUSTED") is False
    assert validate_event_trust("random_string") is False


def test_is_action_supported():
    """Verify supported actions vs invalid actions."""
    assert is_action_supported(RecoveryAction.RETRY) is True
    assert is_action_supported(RecoveryAction.PAYMENT_LINK) is True
    assert is_action_supported(None) is True
