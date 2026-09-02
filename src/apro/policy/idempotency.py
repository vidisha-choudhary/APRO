"""Deterministic idempotency key generation and conflict detection."""

from collections.abc import Sequence

from apro.policy.models import IdempotencyIdentity
from apro.recovery_prediction.enums import RecoveryAction


def generate_idempotency_key(
    case_id: str,
    action: RecoveryAction,
    execution_attempt: int,
) -> str:
    """Generate a deterministic canonical idempotency key."""
    return f"idem_{case_id}_{action.value}_{execution_attempt}"


def build_idempotency_identity(
    case_id: str,
    action: RecoveryAction,
    execution_attempt: int,
) -> IdempotencyIdentity:
    """Build an immutable IdempotencyIdentity structure."""
    key = generate_idempotency_key(case_id, action, execution_attempt)
    return IdempotencyIdentity(
        case_id=case_id,
        action=action,
        execution_attempt=execution_attempt,
        key=key,
    )


def is_idempotency_conflict(
    key: str,
    executed_keys: Sequence[str] | set[str],
) -> bool:
    """Check if the idempotency key has already been executed."""
    return key in executed_keys


__all__ = [
    "build_idempotency_identity",
    "generate_idempotency_key",
    "is_idempotency_conflict",
]
