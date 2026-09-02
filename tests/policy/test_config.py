"""Unit tests for Phase 10 PolicyConfig validation, thresholds, and hash identity."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from apro.policy.config import DEFAULT_POLICY_CONFIG, PolicyConfig


def test_default_policy_config_validity():
    """Verify default policy configuration has valid defaults."""
    cfg = DEFAULT_POLICY_CONFIG
    assert cfg.max_retries == 3
    assert cfg.retry_cooldown_seconds == 300
    assert cfg.max_same_action_repetitions == 2
    assert cfg.max_total_interventions == 4
    assert cfg.high_value_threshold == 100000
    assert cfg.min_decision_confidence == 0.50
    assert cfg.min_expected_recovery_value == 100
    assert cfg.max_payment_link_creations == 2
    assert cfg.approval_expiry_seconds == 86400


def test_policy_config_validation_constraints():
    """Verify invalid threshold and limit constraints raise ValidationError."""
    with pytest.raises(ValidationError):
        PolicyConfig(max_retries=-1)

    with pytest.raises(ValidationError):
        PolicyConfig(min_decision_confidence=1.5)

    with pytest.raises(ValidationError):
        PolicyConfig(min_decision_confidence=-0.1)

    with pytest.raises(ValidationError):
        PolicyConfig(high_value_threshold=-100)


def test_deterministic_identity_excludes_timestamp():
    """Verify compute_deterministic_identity produces identical hash
    regardless of effective_at.
    """
    t1 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    cfg1 = PolicyConfig(max_retries=3, effective_at=t1)
    cfg2 = PolicyConfig(max_retries=3, effective_at=t2)
    cfg3 = PolicyConfig(max_retries=3, effective_at=None)

    id1 = cfg1.compute_deterministic_identity()
    id2 = cfg2.compute_deterministic_identity()
    id3 = cfg3.compute_deterministic_identity()

    assert id1 == id2 == id3
    assert len(id1) == 64  # SHA-256 hex string


def test_deterministic_identity_detects_parameter_changes():
    """Verify changing thresholds results in different hash identity."""
    cfg1 = PolicyConfig(max_retries=3)
    cfg2 = PolicyConfig(max_retries=4)

    assert (
        cfg1.compute_deterministic_identity() != cfg2.compute_deterministic_identity()
    )


def test_policy_config_serialization_roundtrip():
    """Verify to_dict and from_dict serialization round-trip."""
    t = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    cfg = PolicyConfig(
        max_retries=5,
        high_value_threshold=200000,
        effective_at=t,
    )
    data = cfg.to_dict()
    reloaded = PolicyConfig.from_dict(data)

    assert reloaded.max_retries == cfg.max_retries
    assert reloaded.high_value_threshold == cfg.high_value_threshold
    assert reloaded.effective_at == cfg.effective_at
    assert (
        reloaded.compute_deterministic_identity()
        == cfg.compute_deterministic_identity()
    )
