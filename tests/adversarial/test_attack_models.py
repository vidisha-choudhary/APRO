"""Unit tests for immutable Phase 17 attack models and canonical hashing."""

import pytest
from pydantic import ValidationError

from apro.adversarial.enums import (
    AttackCategory,
    AttackDisposition,
    ScenarioId,
)
from apro.adversarial.models import (
    AttackCase,
    AttackResult,
    compute_canonical_hash,
)


def test_attack_case_immutability_and_manifest_hash() -> None:
    """AttackCase is strictly immutable (frozen) and computes deterministic input_manifest_hash."""
    case = AttackCase.create(
        attack_id="att_test_001",
        scenario_id=ScenarioId.SCENARIO_01_POLICY_BYPASS,
        category=AttackCategory.AUTH,
        target_component="PolicyEngine",
        expected_property="Action blocked",
        input_payload={"outcome": "BLOCK"},
        seed=1701,
    )

    assert case.attack_id == "att_test_001"
    assert len(case.input_manifest_hash) == 64
    assert case.category == AttackCategory.AUTH

    # Immutability check
    with pytest.raises(ValidationError):
        case.attack_id = "mutated_id"  # type: ignore[misc]


def test_attack_result_immutability_and_evidence_hash() -> None:
    """AttackResult is immutable and computes deterministic evidence_hash."""
    res = AttackResult.create(
        attack_id="att_test_001",
        scenario_id=ScenarioId.SCENARIO_01_POLICY_BYPASS,
        disposition=AttackDisposition.BLOCKED,
        passed=True,
        expected_property="Action blocked",
        observed_property="Execution blocked by ExecutionAuthorizationError",
        sanitized_evidence={"blocked": True},
        exception_type="ExecutionAuthorizationError",
    )

    assert res.passed is True
    assert res.disposition == AttackDisposition.BLOCKED
    assert len(res.evidence_hash) == 64

    # Immutability check
    with pytest.raises(ValidationError):
        res.passed = False  # type: ignore[misc]


def test_canonical_hash_stability() -> None:
    """Canonical hashing produces identical SHA-256 digests across different key orderings."""
    dict1 = {"b": 2, "a": 1, "c": {"y": "val", "x": 10}}
    dict2 = {"a": 1, "c": {"x": 10, "y": "val"}, "b": 2}

    assert compute_canonical_hash(dict1) == compute_canonical_hash(dict2)
