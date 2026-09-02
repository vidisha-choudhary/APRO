"""Validation and precondition guards for the APRO Execution Framework."""

import uuid
from datetime import UTC, datetime
from typing import Any

from apro.domain.enums import (
    ExecutionMode,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Payment, RecoveryAction, RecoveryCase
from apro.execution.exceptions import (
    ExecutionAuthorizationError,
    ExecutionStateError,
    ExecutionValidationError,
)
from apro.execution.models import ApprovedExecutionRequest
from apro.policy.enums import PolicyOutcome
from apro.policy.models import PolicyDecision

FORBIDDEN_SECRET_KEYS = {
    "api_key",
    "api_secret",
    "secret",
    "password",
    "access_token",
    "token",
    "card_number",
    "cvv",
    "cvv_number",
    "private_key",
}

_EXECUTION_ELIGIBLE_CASE_STATES = {
    RecoveryCaseStatus.POLICY_CHECK,
    RecoveryCaseStatus.ACTION_APPROVED,
    RecoveryCaseStatus.EXECUTING,
}


def _norm_action(val: str) -> str:
    """Normalize action string to support domain synonyms."""
    if val in ("PAYMENT_LINK", "ALTERNATE_RECOVERY"):
        return "PAYMENT_LINK"
    return val


def validate_parameter_secrets(parameters: dict[str, Any] | None) -> None:
    """Ensure no credentials or secret keys are present in parameters."""
    if not parameters:
        return
    for k in parameters:
        lower_k = k.lower()
        if lower_k in FORBIDDEN_SECRET_KEYS or any(
            sec in lower_k for sec in ("secret", "password", "token")
        ):
            msg = f"Forbidden credential/secret key '{k}' found in parameters."
            raise ExecutionValidationError(msg)


def validate_policy_authorization(
    policy_decision: PolicyDecision,
    action: RecoveryAction,
    case: RecoveryCase,
    payment: Payment,
) -> None:
    """Validate that the execution is strictly authorized by PolicyDecision.

    Raises:
        ExecutionAuthorizationError: If outcome is not ALLOW or approvals missing.
        ExecutionValidationError: If entity IDs or actions do not match.
    """
    # 1. Check Policy Outcome
    if policy_decision.policy_outcome == PolicyOutcome.BLOCK:
        msg = (
            f"Execution rejected: PolicyDecision {policy_decision.policy_decision_id} "
            f"has outcome BLOCK (reason: {policy_decision.reason_code.value})."
        )
        raise ExecutionAuthorizationError(msg)

    if (
        policy_decision.policy_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
        and not policy_decision.approval_reference
    ):
        msg = (
            f"Execution rejected: PolicyDecision {policy_decision.policy_decision_id} "
            "requires human approval but no approval reference was authorized."
        )
        raise ExecutionAuthorizationError(msg)

    if policy_decision.policy_outcome != PolicyOutcome.ALLOW:
        outcome_val = policy_decision.policy_outcome.value
        msg = f"Execution rejected: Policy outcome '{outcome_val}' is not ALLOW."
        raise ExecutionAuthorizationError(msg)

    # 2. Check Effective Action
    if policy_decision.effective_action is None:
        msg = (
            "Execution rejected: PolicyDecision has ALLOW outcome "
            "but missing effective_action."
        )
        raise ExecutionAuthorizationError(msg)

    # 3. Action Matching (normalized)
    act_norm = _norm_action(action.action_type.value)
    pol_norm = _norm_action(policy_decision.effective_action.value)
    if act_norm != pol_norm:
        msg = (
            f"Action mismatch: Policy authorized "
            f"'{policy_decision.effective_action.value}' "
            f"but requested execution action is '{action.action_type.value}'."
        )
        raise ExecutionValidationError(msg)

    # 4. Entity Binding
    if policy_decision.case_id != case.case_id:
        msg = (
            f"Case mismatch: PolicyDecision case_id '{policy_decision.case_id}' "
            f"does not match RecoveryCase case_id '{case.case_id}'."
        )
        raise ExecutionValidationError(msg)

    if action.case_id != case.case_id:
        msg = (
            f"Action-Case mismatch: RecoveryAction case_id '{action.case_id}' "
            f"does not match RecoveryCase case_id '{case.case_id}'."
        )
        raise ExecutionValidationError(msg)

    if policy_decision.payment_id != payment.payment_id:
        msg = (
            f"Payment mismatch: PolicyDecision payment_id "
            f"'{policy_decision.payment_id}' "
            f"does not match Payment payment_id '{payment.payment_id}'."
        )
        raise ExecutionValidationError(msg)


def validate_execution_preconditions(
    action: RecoveryAction,
    case: RecoveryCase,
    payment: Payment,
    execution_mode: ExecutionMode | None = None,
    parameters: dict[str, Any] | None = None,
) -> None:
    """Validate payment, case, action lifecycle, and parameters before dispatch.

    Raises:
        ExecutionStateError: If current entity states prohibit execution.
        ExecutionValidationError: If parameters fail validation.
    """
    _ = execution_mode
    # 1. Payment state safety
    if payment.status == PaymentStatus.CAPTURED:
        msg = (
            f"Cannot execute action for payment {payment.payment_id}: "
            "status is CAPTURED."
        )
        raise ExecutionStateError(msg)

    # 2. Case state eligibility
    if case.status not in _EXECUTION_ELIGIBLE_CASE_STATES:
        msg = (
            f"RecoveryCase {case.case_id} status '{case.status.value}' "
            "is not execution-eligible."
        )
        raise ExecutionStateError(msg)

    # 3. Action state eligibility
    if action.status in (
        RecoveryActionStatus.COMPLETED,
        RecoveryActionStatus.FAILED,
        RecoveryActionStatus.CANCELLED,
        RecoveryActionStatus.BLOCKED,
    ):
        msg = (
            f"RecoveryAction {action.action_id} is in terminal state "
            f"'{action.status.value}'."
        )
        raise ExecutionStateError(msg)

    # 4. Parameter validation
    validate_parameter_secrets(parameters or action.parameters)


def build_approved_execution_request(
    policy_decision: PolicyDecision,
    action: RecoveryAction,
    case: RecoveryCase,
    execution_mode: ExecutionMode,
    current_time: datetime | None = None,
    parameters: dict[str, Any] | None = None,
    execution_id: str | None = None,
) -> ApprovedExecutionRequest:
    """Construct an immutable ApprovedExecutionRequest from validated context."""
    now = current_time or datetime.now(UTC)
    action_val = action.action_type.value
    idem_key = policy_decision.idempotency_key or f"idem_{case.case_id}_{action_val}_1"
    exec_id = execution_id or str(uuid.uuid4())
    combined_params = dict(action.parameters or {})
    if parameters:
        combined_params.update(parameters)

    return ApprovedExecutionRequest(
        execution_id=exec_id,
        case_id=case.case_id,
        action_id=action.action_id,
        action_type=RecoveryActionType(action.action_type.value),
        policy_decision_id=policy_decision.policy_decision_id,
        decision_id=policy_decision.decision_id,
        idempotency_key=idem_key,
        execution_mode=execution_mode,
        parameters=combined_params,
        requested_at=now,
        policy_version=policy_decision.policy_version,
        rule_set_version=policy_decision.rule_set_version,
        action_schema_version=policy_decision.action_schema_version,
        approval_reference=policy_decision.approval_reference,
    )


__all__ = [
    "FORBIDDEN_SECRET_KEYS",
    "build_approved_execution_request",
    "validate_execution_preconditions",
    "validate_parameter_secrets",
    "validate_policy_authorization",
]
