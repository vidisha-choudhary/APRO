"""Unit tests for Phase 10 human approval binding, action specificity,
replay protection, and expiry enforcement.
"""

from datetime import UTC, datetime, timedelta

from apro.policy.approvals import validate_human_approval
from apro.policy.enums import PolicyReasonCode
from apro.policy.models import ApprovalRecord
from apro.recovery_prediction.enums import RecoveryAction


def make_valid_approval(
    case_id: str = "case_001",
    decision_id: str = "dec_001",
    action: RecoveryAction = RecoveryAction.RETRY,
    expires_in_hours: int = 24,
    approval_id: str = "appr_001",
) -> ApprovalRecord:
    now = datetime.now(UTC)
    return ApprovalRecord(
        approval_id=approval_id,
        case_id=case_id,
        decision_id=decision_id,
        approved_action=action,
        approver_reference="ops_lead_01",
        approved_at=now,
        expires_at=now + timedelta(hours=expires_in_hours),
        policy_version="policy-v1",
    )


def test_validate_approval_missing():
    """Verify missing approval returns APPROVAL_REQUIRED."""
    now = datetime.now(UTC)
    valid, reason, _ = validate_human_approval(
        None, "case_001", "dec_001", RecoveryAction.RETRY, now, "policy-v1"
    )
    assert valid is False
    assert reason == PolicyReasonCode.APPROVAL_REQUIRED


def test_validate_approval_valid_first_use():
    """Verify matching valid approval passes on first use."""
    now = datetime.now(UTC)
    appr = make_valid_approval(
        case_id="case_001", decision_id="dec_001", action=RecoveryAction.RETRY
    )
    valid, reason, _ = validate_human_approval(
        appr,
        "case_001",
        "dec_001",
        RecoveryAction.RETRY,
        now,
        "policy-v1",
        executed_approval_ids=(),
    )
    assert valid is True
    assert reason is None


def test_validate_approval_replay_rejected():
    """Verify consumed approval is rejected under replay protection."""
    now = datetime.now(UTC)
    appr = make_valid_approval(
        approval_id="appr_001",
        case_id="case_001",
        decision_id="dec_001",
        action=RecoveryAction.RETRY,
    )
    # Simulate that appr_001 was already executed on previous attempt
    valid, reason, detail = validate_human_approval(
        appr,
        "case_001",
        "dec_001",
        RecoveryAction.RETRY,
        now,
        "policy-v1",
        executed_approval_ids=("appr_001",),
    )
    assert valid is False
    assert reason == PolicyReasonCode.APPROVAL_MISMATCH
    assert "replay is strictly prohibited" in str(detail)


def test_validate_approval_case_mismatch():
    """Verify approval for different case is rejected."""
    now = datetime.now(UTC)
    appr = make_valid_approval(
        case_id="case_other", decision_id="dec_001", action=RecoveryAction.RETRY
    )
    valid, reason, _ = validate_human_approval(
        appr, "case_001", "dec_001", RecoveryAction.RETRY, now, "policy-v1"
    )
    assert valid is False
    assert reason == PolicyReasonCode.APPROVAL_MISMATCH


def test_validate_approval_decision_mutation_rejected():
    """Verify approval is invalidated if decision_id mutated."""
    now = datetime.now(UTC)
    appr = make_valid_approval(
        case_id="case_001", decision_id="dec_orig_001", action=RecoveryAction.RETRY
    )
    # Decision was mutated/re-computed with new ID
    valid, reason, _ = validate_human_approval(
        appr, "case_001", "dec_mutated_002", RecoveryAction.RETRY, now, "policy-v1"
    )
    assert valid is False
    assert reason == PolicyReasonCode.APPROVAL_MISMATCH


def test_validate_approval_action_mismatch():
    """Verify approval for PAYMENT_LINK does not authorize RETRY."""
    now = datetime.now(UTC)
    appr = make_valid_approval(
        case_id="case_001",
        decision_id="dec_001",
        action=RecoveryAction.PAYMENT_LINK,
    )
    valid, reason, _ = validate_human_approval(
        appr, "case_001", "dec_001", RecoveryAction.RETRY, now, "policy-v1"
    )
    assert valid is False
    assert reason == PolicyReasonCode.APPROVAL_MISMATCH


def test_validate_approval_expired():
    """Verify expired approval is rejected."""
    now = datetime.now(UTC)
    appr = make_valid_approval(
        case_id="case_001",
        decision_id="dec_001",
        action=RecoveryAction.RETRY,
        expires_in_hours=-1,  # Expired 1 hour ago
    )
    valid, reason, _ = validate_human_approval(
        appr, "case_001", "dec_001", RecoveryAction.RETRY, now, "policy-v1"
    )
    assert valid is False
    assert reason == PolicyReasonCode.APPROVAL_EXPIRED


def test_validate_approval_incompatible_policy_version():
    """Verify approval issued under different policy version is rejected."""
    now = datetime.now(UTC)
    appr = make_valid_approval(
        case_id="case_001",
        decision_id="dec_001",
        action=RecoveryAction.RETRY,
    )
    # Expected version is policy-v2, while approval was issued under policy-v1
    valid, reason, _ = validate_human_approval(
        appr, "case_001", "dec_001", RecoveryAction.RETRY, now, "policy-v2"
    )
    assert valid is False
    assert reason == PolicyReasonCode.APPROVAL_MISMATCH
