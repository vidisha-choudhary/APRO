"""Unit tests for Phase 10 idempotency key generation and conflict detection."""

from apro.policy.idempotency import (
    build_idempotency_identity,
    generate_idempotency_key,
    is_idempotency_conflict,
)
from apro.recovery_prediction.enums import RecoveryAction


def test_generate_idempotency_key_canonical_format():
    """Verify exact canonical format of generated idempotency keys."""
    k1 = generate_idempotency_key("case_123", RecoveryAction.RETRY, 1)
    k2 = generate_idempotency_key("case_123", RecoveryAction.PAYMENT_LINK, 2)
    k3 = generate_idempotency_key("case_456", RecoveryAction.OUTREACH, 3)

    assert k1 == "idem_case_123_RETRY_1"
    assert k2 == "idem_case_123_PAYMENT_LINK_2"
    assert k3 == "idem_case_456_OUTREACH_3"


def test_build_idempotency_identity():
    """Verify IdempotencyIdentity structure."""
    ident = build_idempotency_identity("case_999", RecoveryAction.OUTREACH, 1)
    assert ident.case_id == "case_999"
    assert ident.action == RecoveryAction.OUTREACH
    assert ident.execution_attempt == 1
    assert ident.key == "idem_case_999_OUTREACH_1"


def test_is_idempotency_conflict():
    """Verify conflict detection against historical executed keys."""
    executed = ("idem_case_1_RETRY_1", "idem_case_1_RETRY_2")
    assert is_idempotency_conflict("idem_case_1_RETRY_1", executed) is True
    assert is_idempotency_conflict("idem_case_1_RETRY_3", executed) is False
