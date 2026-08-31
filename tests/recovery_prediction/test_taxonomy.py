"""Unit tests for Phase 8 action and outcome taxonomies."""

from apro.recovery_prediction.enums import (
    OUTCOME_TAXONOMY_ORDER,
    OUTCOME_TAXONOMY_VERSION,
    RECOVERY_ACTION_ORDER,
    RECOVERY_ACTION_SCHEMA_VERSION,
    PredictedOutcomeState,
    PredictionUncertaintyState,
    RecoveryAction,
)


def test_action_taxonomy_and_order() -> None:
    """AC-01: Verify all 5 recovery actions exist and have deterministic ordering."""
    expected_actions = (
        RecoveryAction.RETRY,
        RecoveryAction.PAYMENT_LINK,
        RecoveryAction.OUTREACH,
        RecoveryAction.STOP,
        RecoveryAction.ESCALATE,
    )
    assert expected_actions == RECOVERY_ACTION_ORDER
    assert len(RECOVERY_ACTION_ORDER) == 5
    assert RECOVERY_ACTION_SCHEMA_VERSION == "recovery-action-v1"


def test_outcome_taxonomy_and_uncertainty() -> None:
    """AC-12, AC-22: Verify outcome states and uncertainty enumeration."""
    assert len(OUTCOME_TAXONOMY_ORDER) == 3
    assert PredictedOutcomeState.SUCCESS in OUTCOME_TAXONOMY_ORDER
    assert PredictedOutcomeState.FAILURE in OUTCOME_TAXONOMY_ORDER
    assert PredictedOutcomeState.PENDING in OUTCOME_TAXONOMY_ORDER
    assert OUTCOME_TAXONOMY_VERSION == "recovery-outcome-taxonomy-v1"

    assert PredictionUncertaintyState.HIGH_CONFIDENCE == "HIGH_CONFIDENCE"
    assert PredictionUncertaintyState.MEDIUM_CONFIDENCE == "MEDIUM_CONFIDENCE"
    assert PredictionUncertaintyState.LOW_CONFIDENCE == "LOW_CONFIDENCE"
    assert PredictionUncertaintyState.ABSTAIN == "ABSTAIN"
