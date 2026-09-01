"""Taxonomies, vocabulary constants, and enums for APRO Phase 9."""

from enum import StrEnum

from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_ORDER,
    RECOVERY_ACTION_SCHEMA_VERSION,
    RecoveryAction,
)

DECISION_STATUS_SCHEMA_VERSION: str = "decision-status-v1"
DECISION_MODEL_SCHEMA_VERSION: str = "decision-model-v1"
ECONOMIC_CONFIG_SCHEMA_VERSION: str = "economic-config-v1"
POLICY_CONFIG_SCHEMA_VERSION: str = "policy-config-v1"
UTILITY_FORMULA_VERSION: str = "utility-formula-v1"


class DecisionStatus(StrEnum):
    """Decision status outcome classification."""

    ACTION_SELECTED = "ACTION_SELECTED"
    NO_ELIGIBLE_ACTION = "NO_ELIGIBLE_ACTION"
    NO_POSITIVE_UTILITY = "NO_POSITIVE_UTILITY"
    ABSTAIN = "ABSTAIN"


DEFAULT_TIE_BREAK_ORDER: tuple[RecoveryAction, ...] = (
    RecoveryAction.STOP,
    RecoveryAction.ESCALATE,
    RecoveryAction.RETRY,
    RecoveryAction.PAYMENT_LINK,
    RecoveryAction.OUTREACH,
)

__all__ = [
    "DECISION_MODEL_SCHEMA_VERSION",
    "DECISION_STATUS_SCHEMA_VERSION",
    "DEFAULT_TIE_BREAK_ORDER",
    "ECONOMIC_CONFIG_SCHEMA_VERSION",
    "POLICY_CONFIG_SCHEMA_VERSION",
    "RECOVERY_ACTION_ORDER",
    "RECOVERY_ACTION_SCHEMA_VERSION",
    "UTILITY_FORMULA_VERSION",
    "DecisionStatus",
    "RecoveryAction",
]
