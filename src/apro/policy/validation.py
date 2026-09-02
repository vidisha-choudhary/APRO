"""Input validation and fail-closed integrity checks for Phase 10."""

import math
from typing import Any

from apro.decision.models import RecoveryDecision
from apro.domain.models import Payment, RecoveryCase
from apro.policy.models import EventTrustState
from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_ORDER,
    RecoveryAction,
)


def is_valid_probability(value: Any) -> bool:
    """Check whether value is a valid probability in [0.0, 1.0]."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    if math.isnan(value) or math.isinf(value):
        return False
    return 0.0 <= float(value) <= 1.0


def is_valid_currency_amount(value: Any, max_allowed: int | None = None) -> bool:
    """Check whether monetary amount is a non-negative integer within bounds."""
    if not isinstance(value, int) or isinstance(value, bool):
        return False
    if value < 0:
        return False
    return not (max_allowed is not None and value > max_allowed)


def validate_entity_binding(
    payment: Payment,
    case: RecoveryCase,
    decision: RecoveryDecision,
) -> tuple[bool, str | None]:
    """Validate entity binding across Payment, Case, and Decision."""
    if payment.payment_id != case.payment_id:
        return (
            False,
            f"Entity binding error: Payment ID '{payment.payment_id}' does not "
            f"match RecoveryCase.payment_id '{case.payment_id}'",
        )
    if case.case_id != decision.recovery_case_id:
        return (
            False,
            f"Entity binding error: Case ID '{case.case_id}' does not "
            f"match RecoveryDecision.recovery_case_id '{decision.recovery_case_id}'",
        )
    return True, None


def validate_recovery_decision_model_output(
    decision: RecoveryDecision,
    payment: Payment,
) -> tuple[bool, str | None]:
    """Validate Phase 9 RecoveryDecision against strict fail-closed constraints."""
    # 1. Decision confidence validation
    if not is_valid_probability(decision.decision_confidence):
        return False, "decision_confidence is not a valid probability in [0, 1]"

    # 2. Selected action validation
    if (
        decision.selected_action is not None
        and decision.selected_action not in RECOVERY_ACTION_ORDER
    ):
        return (
            False,
            f"selected_action '{decision.selected_action}' "
            "is not in supported taxonomy",
        )

    # 3. Utilities validation
    if not decision.utility_by_action:
        return False, "utility_by_action mapping is empty"

    for action, utility in decision.utility_by_action.items():
        if action not in RECOVERY_ACTION_ORDER:
            return False, f"utility key '{action}' is not a valid RecoveryAction"

        if not is_valid_probability(utility.predicted_success_probability):
            return (
                False,
                f"predicted_success_probability for action {action} "
                "is invalid or NaN/Inf",
            )

        if not is_valid_currency_amount(
            utility.predicted_recovered_amount, max_allowed=payment.amount
        ):
            msg = (
                f"predicted_recovered_amount ({utility.predicted_recovered_amount}) "
                f"for action {action} is negative or exceeds "
                f"payment amount ({payment.amount})"
            )
            return (
                False,
                msg,
            )

        if (
            utility.action_cost < 0
            or utility.operational_cost < 0
            or utility.customer_friction_cost < 0
            or utility.risk_penalty < 0
        ):
            return False, f"cost components for action {action} contain negative values"

        if math.isnan(utility.expected_recovery_value) or math.isinf(
            utility.expected_recovery_value
        ):
            return (
                False,
                f"expected_recovery_value for action {action} is NaN or infinite",
            )

    return True, None


def validate_event_trust(event_trust: EventTrustState | bool | str | None) -> bool:
    """Determine whether an incoming event signature/origin is trusted (fail-closed)."""
    if event_trust is None:
        return False
    if isinstance(event_trust, bool):
        return event_trust
    if isinstance(event_trust, EventTrustState):
        return event_trust == EventTrustState.TRUSTED
    if isinstance(event_trust, str):
        return event_trust.upper() == EventTrustState.TRUSTED.value
    return False


def is_action_supported(action: RecoveryAction | None) -> bool:
    """Verify that an action belongs to the supported 5-action taxonomy."""
    if action is None:
        return True
    return action in RECOVERY_ACTION_ORDER


__all__ = [
    "is_action_supported",
    "is_valid_currency_amount",
    "is_valid_probability",
    "validate_entity_binding",
    "validate_event_trust",
    "validate_recovery_decision_model_output",
]
