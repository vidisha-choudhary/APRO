"""Enumerations, taxonomies, and vocabulary constants for APRO Phase 8."""

from enum import StrEnum


class RecoveryAction(StrEnum):
    """Candidate recovery actions evaluated by Model B."""

    RETRY = "RETRY"
    PAYMENT_LINK = "PAYMENT_LINK"
    OUTREACH = "OUTREACH"
    STOP = "STOP"
    ESCALATE = "ESCALATE"


RECOVERY_ACTION_ORDER: tuple[RecoveryAction, ...] = (
    RecoveryAction.RETRY,
    RecoveryAction.PAYMENT_LINK,
    RecoveryAction.OUTREACH,
    RecoveryAction.STOP,
    RecoveryAction.ESCALATE,
)

RECOVERY_ACTION_SCHEMA_VERSION: str = "recovery-action-v1"


class PredictedOutcomeState(StrEnum):
    """Predicted outcome state vocabulary for an executed recovery action."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"


OUTCOME_TAXONOMY_ORDER: tuple[PredictedOutcomeState, ...] = (
    PredictedOutcomeState.SUCCESS,
    PredictedOutcomeState.FAILURE,
    PredictedOutcomeState.PENDING,
)

OUTCOME_TAXONOMY_VERSION: str = "recovery-outcome-taxonomy-v1"


class PredictionUncertaintyState(StrEnum):
    """Structured confidence and uncertainty states for Model B predictions."""

    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    MEDIUM_CONFIDENCE = "MEDIUM_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    ABSTAIN = "ABSTAIN"


class RecoveryAlgorithmType(StrEnum):
    """Algorithm identifiers for Model B and baseline models."""

    GLOBAL_ACTION_RATE = "GLOBAL_ACTION_RATE"
    ACTION_STRATIFIED_HISTORICAL = "ACTION_STRATIFIED_HISTORICAL"
    STATIC_OUTCOME_RULE = "STATIC_OUTCOME_RULE"
    STATISTICAL_ACTION_BASELINE = "STATISTICAL_ACTION_BASELINE"
    LOGISTIC_REGRESSION = "LOGISTIC_REGRESSION"
    DECISION_TREE = "DECISION_TREE"
    RANDOM_FOREST = "RANDOM_FOREST"
