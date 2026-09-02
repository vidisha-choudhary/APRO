"""Human approval verification, case binding, action specificity, and expiry."""

from collections.abc import Sequence
from datetime import datetime

from apro.policy.enums import PolicyReasonCode
from apro.policy.models import ApprovalRecord
from apro.recovery_prediction.enums import RecoveryAction


def validate_human_approval(
    approval: ApprovalRecord | None,
    case_id: str,
    decision_id: str | None,
    requested_action: RecoveryAction | None,
    current_time: datetime,
    expected_policy_version: str,
    executed_approval_ids: Sequence[str] | None = None,
) -> tuple[bool, PolicyReasonCode | None, str | None]:
    """Verify human approval token against strict binding and replay constraints."""
    if approval is None:
        return (
            False,
            PolicyReasonCode.APPROVAL_REQUIRED,
            "Action requires human approval, but no approval token was provided.",
        )

    # 1. Replay Protection
    if executed_approval_ids and approval.approval_id in executed_approval_ids:
        return (
            False,
            PolicyReasonCode.APPROVAL_MISMATCH,
            f"Approval '{approval.approval_id}' has already been consumed or "
            "executed. Approval replay is strictly prohibited.",
        )

    # 2. Case Binding
    if approval.case_id != case_id:
        return (
            False,
            PolicyReasonCode.APPROVAL_MISMATCH,
            f"Approval case ID '{approval.case_id}' does not match "
            f"target case ID '{case_id}'.",
        )

    # 3. Decision Binding
    if decision_id and approval.decision_id != decision_id:
        return (
            False,
            PolicyReasonCode.APPROVAL_MISMATCH,
            f"Approval decision ID '{approval.decision_id}' does not match "
            f"target decision ID '{decision_id}'.",
        )

    # 4. Action Specificity
    if requested_action is None or approval.approved_action != requested_action:
        req_act_str = requested_action.value if requested_action else "None"
        return (
            False,
            PolicyReasonCode.APPROVAL_MISMATCH,
            f"Approval action '{approval.approved_action.value}' does not "
            f"authorize requested action '{req_act_str}'.",
        )

    # 5. Expiration Check
    if approval.expires_at is not None and current_time > approval.expires_at:
        return (
            False,
            PolicyReasonCode.APPROVAL_EXPIRED,
            f"Approval expired at {approval.expires_at.isoformat()} "
            f"(current evaluation time: {current_time.isoformat()}).",
        )

    # 6. Policy Version Compatibility
    if approval.policy_version != expected_policy_version:
        return (
            False,
            PolicyReasonCode.APPROVAL_MISMATCH,
            f"Approval was issued under policy version '{approval.policy_version}', "
            f"which is incompatible with current version '{expected_policy_version}'.",
        )

    return True, None, None


__all__ = ["validate_human_approval"]
