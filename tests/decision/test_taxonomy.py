"""Unit tests for Phase 9 taxonomies, vocabularies, and deterministic order."""

from apro.decision.enums import (
    DECISION_MODEL_SCHEMA_VERSION,
    DECISION_STATUS_SCHEMA_VERSION,
    DEFAULT_TIE_BREAK_ORDER,
    ECONOMIC_CONFIG_SCHEMA_VERSION,
    POLICY_CONFIG_SCHEMA_VERSION,
    RECOVERY_ACTION_ORDER,
    RECOVERY_ACTION_SCHEMA_VERSION,
    UTILITY_FORMULA_VERSION,
    DecisionStatus,
    RecoveryAction,
)


def test_action_taxonomy_and_order() -> None:
    """Verify exact 5 recovery actions and their deterministic ordering."""
    assert len(RecoveryAction) == 5
    assert len(RECOVERY_ACTION_ORDER) == 5

    expected_order = (
        RecoveryAction.RETRY,
        RecoveryAction.PAYMENT_LINK,
        RecoveryAction.OUTREACH,
        RecoveryAction.STOP,
        RecoveryAction.ESCALATE,
    )
    assert expected_order == RECOVERY_ACTION_ORDER
    assert RECOVERY_ACTION_SCHEMA_VERSION == "recovery-action-v1"


def test_decision_status_taxonomy() -> None:
    """Verify decision status enum and schema version."""
    assert len(DecisionStatus) == 4
    expected_statuses = {
        "ACTION_SELECTED",
        "NO_ELIGIBLE_ACTION",
        "NO_POSITIVE_UTILITY",
        "ABSTAIN",
    }
    assert {s.value for s in DecisionStatus} == expected_statuses
    assert DECISION_STATUS_SCHEMA_VERSION == "decision-status-v1"


def test_schema_versions_and_tie_break_order() -> None:
    """Verify version constants and default tie-break order."""
    assert DECISION_MODEL_SCHEMA_VERSION == "decision-model-v1"
    assert ECONOMIC_CONFIG_SCHEMA_VERSION == "economic-config-v1"
    assert POLICY_CONFIG_SCHEMA_VERSION == "policy-config-v1"
    assert UTILITY_FORMULA_VERSION == "utility-formula-v1"

    expected_tie_break = (
        RecoveryAction.STOP,
        RecoveryAction.ESCALATE,
        RecoveryAction.RETRY,
        RecoveryAction.PAYMENT_LINK,
        RecoveryAction.OUTREACH,
    )
    assert expected_tie_break == DEFAULT_TIE_BREAK_ORDER
