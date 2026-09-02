"""Unit tests for Phase 10 taxonomies, enums, reason codes, and rule identifiers."""

from apro.policy.enums import (
    POLICY_ARTIFACT_SCHEMA_VERSION,
    POLICY_DECISION_SCHEMA_VERSION,
    POLICY_SCHEMA_VERSION,
    POLICY_TRACE_SCHEMA_VERSION,
    POLICY_VERSION,
    RULE_SET_VERSION,
    PolicyOutcome,
    PolicyReasonCode,
    RuleId,
    RulePrecedenceLevel,
)


def test_policy_outcomes_enumeration():
    """Verify explicit three-state policy outcome vocabulary."""
    outcomes = set(PolicyOutcome)
    assert outcomes == {
        PolicyOutcome.ALLOW,
        PolicyOutcome.BLOCK,
        PolicyOutcome.REQUIRE_HUMAN_APPROVAL,
    }
    assert len(PolicyOutcome) == 3


def test_policy_reason_codes():
    """Verify standard machine-readable reason codes."""
    assert PolicyReasonCode.PAYMENT_ALREADY_RECOVERED == "PAYMENT_ALREADY_RECOVERED"
    assert PolicyReasonCode.INVALID_EVENT == "INVALID_EVENT"
    assert PolicyReasonCode.DUPLICATE_EVENT == "DUPLICATE_EVENT"
    assert PolicyReasonCode.UNSUPPORTED_ACTION == "UNSUPPORTED_ACTION"
    assert PolicyReasonCode.INVALID_MODEL_OUTPUT == "INVALID_MODEL_OUTPUT"
    assert PolicyReasonCode.MAX_RETRIES_REACHED == "MAX_RETRIES_REACHED"
    assert PolicyReasonCode.RETRY_COOLDOWN_ACTIVE == "RETRY_COOLDOWN_ACTIVE"
    assert (
        PolicyReasonCode.MAX_SAME_ACTION_REPETITIONS_REACHED
        == "MAX_SAME_ACTION_REPETITIONS_REACHED"
    )
    assert (
        PolicyReasonCode.MAX_TOTAL_INTERVENTIONS_REACHED
        == "MAX_TOTAL_INTERVENTIONS_REACHED"
    )
    assert (
        PolicyReasonCode.HIGH_VALUE_REQUIRES_APPROVAL == "HIGH_VALUE_REQUIRES_APPROVAL"
    )
    assert (
        PolicyReasonCode.LOW_CONFIDENCE_REQUIRES_APPROVAL
        == "LOW_CONFIDENCE_REQUIRES_APPROVAL"
    )
    assert PolicyReasonCode.INSUFFICIENT_EXPECTED_VALUE == "INSUFFICIENT_EXPECTED_VALUE"
    assert PolicyReasonCode.NEGATIVE_EXPECTED_VALUE == "NEGATIVE_EXPECTED_VALUE"
    assert PolicyReasonCode.STALE_OR_INCONSISTENT_EVENT == "STALE_OR_INCONSISTENT_EVENT"
    assert PolicyReasonCode.RECONCILIATION_REQUIRED == "RECONCILIATION_REQUIRED"
    assert (
        PolicyReasonCode.PAYMENT_LINK_CAPACITY_REACHED
        == "PAYMENT_LINK_CAPACITY_REACHED"
    )
    assert PolicyReasonCode.DUPLICATE_PAYMENT_LINK == "DUPLICATE_PAYMENT_LINK"
    assert PolicyReasonCode.MODEL_A_FAILURE == "MODEL_A_FAILURE"
    assert PolicyReasonCode.MODEL_B_FAILURE == "MODEL_B_FAILURE"
    assert PolicyReasonCode.APPROVAL_REQUIRED == "APPROVAL_REQUIRED"
    assert PolicyReasonCode.APPROVAL_MISMATCH == "APPROVAL_MISMATCH"
    assert PolicyReasonCode.APPROVAL_EXPIRED == "APPROVAL_EXPIRED"
    assert PolicyReasonCode.IDEMPOTENCY_CONFLICT == "IDEMPOTENCY_CONFLICT"
    assert PolicyReasonCode.POLICY_ALLOWED == "POLICY_ALLOWED"


def test_rule_precedence_ordering():
    """Verify deterministic precedence hierarchy (1 is highest priority)."""
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


def test_rule_ids_catalog():
    """Verify all registered rule IDs."""
    rule_ids = set(RuleId)
    assert "H1_PAYMENT_CAPTURED" in rule_ids
    assert "H2_INVALID_EVENT" in rule_ids
    assert "H3_DUPLICATE_EVENT" in rule_ids
    assert "H4_UNSUPPORTED_ACTION" in rule_ids
    assert "H5_INVALID_MODEL_OUTPUT" in rule_ids
    assert "R1_RETRY_LIMIT" in rule_ids
    assert "R2_RETRY_COOLDOWN" in rule_ids
    assert "R3_SAME_ACTION_LIMIT" in rule_ids
    assert "R4_TOTAL_INTERVENTION_LIMIT" in rule_ids
    assert "S1_HIGH_VALUE" in rule_ids
    assert "S2_LOW_CONFIDENCE" in rule_ids
    assert "S3_MIN_ERV" in rule_ids
    assert "S4_NEGATIVE_ERV" in rule_ids
    assert "S5_STALE_STATE" in rule_ids
    assert "S6_RECONCILIATION" in rule_ids
    assert "S7_PAYMENT_LINK_CAPACITY" in rule_ids
    assert "S8_IDEMPOTENCY_CONFLICT" in rule_ids
    assert "A1_APPROVAL_REQUIRED" in rule_ids
    assert "A2_APPROVAL_MISMATCH" in rule_ids
    assert "A3_APPROVAL_EXPIRED" in rule_ids
    assert "M1_MODEL_A_FAILURE" in rule_ids
    assert "M2_MODEL_B_FAILURE" in rule_ids


def test_schema_versions_defined():
    """Verify version string constants."""
    assert POLICY_SCHEMA_VERSION == "policy-config-v1"
    assert POLICY_VERSION == "policy-v1"
    assert RULE_SET_VERSION == "ruleset-v1"
    assert POLICY_DECISION_SCHEMA_VERSION == "policy-decision-v1"
    assert POLICY_TRACE_SCHEMA_VERSION == "policy-trace-v1"
    assert POLICY_ARTIFACT_SCHEMA_VERSION == "policy-artifact-v1"
