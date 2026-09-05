"""Security and safety invariant assertions for Phase 17."""

import json
from typing import Any

from apro.adversarial.enums import AttackDisposition
from apro.adversarial.models import AttackResult


def assert_disposition_is_secure(result: AttackResult) -> None:
    """Assert that the attack result reflects a secure defensive disposition."""
    secure_dispositions = {
        AttackDisposition.BLOCKED,
        AttackDisposition.REJECTED,
        AttackDisposition.CONTAINED,
        AttackDisposition.DETECTED,
        AttackDisposition.EXPECTED_FAILURE,
    }
    if result.disposition not in secure_dispositions or not result.passed:
        raise AssertionError(
            f"Security assertion failed for attack {result.attack_id}: "
            f"observed disposition '{result.disposition}', expected secure disposition. "
            f"Observed property: {result.observed_property}"
        )


def assert_action_unauthorized(result: AttackResult) -> None:
    """Assert that an unauthorized action execution was strictly blocked."""
    assert_disposition_is_secure(result)
    if result.disposition not in (
        AttackDisposition.BLOCKED,
        AttackDisposition.REJECTED,
    ):
        raise AssertionError(
            f"Expected BLOCKED or REJECTED for unauthorized action attack, got {result.disposition}"
        )


def assert_stale_authority_rejected(result: AttackResult) -> None:
    """Assert that stale decision or policy authority was rejected."""
    assert_disposition_is_secure(result)
    if result.disposition not in (
        AttackDisposition.REJECTED,
        AttackDisposition.CONTAINED,
    ):
        raise AssertionError(
            f"Expected REJECTED or CONTAINED for stale authority replay, got {result.disposition}"
        )


def assert_exactly_once_advancement(
    total_replay_attempts: int | None = None,
    authoritative_executions: int | None = None,
    provider_side_effects: int | None = None,
    semantic_outcomes: int | None = None,
    duplicate_advancements: int | None = None,
    *,
    replay_attempt_count: int | None = None,
    authoritative_execution_count: int | None = None,
    provider_simulator_side_effect_count: int | None = None,
    semantic_outcome_count: int | None = None,
    persisted_semantic_outcome_count: int | None = None,
    duplicate_audit_advancement: int | None = None,
    duplicate_advancement_count: int | None = None,
    duplicate_persisted_advancement_count: int | None = None,
) -> None:
    """Assert that a replay storm produced exactly-once semantic advancement."""
    total_replays = (
        replay_attempt_count
        if replay_attempt_count is not None
        else (total_replay_attempts or 0)
    )
    auth_execs = (
        authoritative_execution_count
        if authoritative_execution_count is not None
        else (authoritative_executions or 0)
    )
    provider_effects = (
        provider_simulator_side_effect_count
        if provider_simulator_side_effect_count is not None
        else (provider_side_effects or 0)
    )
    outcomes = (
        persisted_semantic_outcome_count
        if persisted_semantic_outcome_count is not None
        else (
            semantic_outcome_count
            if semantic_outcome_count is not None
            else (semantic_outcomes or 0)
        )
    )
    dup_adv = (
        duplicate_persisted_advancement_count
        if duplicate_persisted_advancement_count is not None
        else (
            duplicate_advancement_count
            if duplicate_advancement_count is not None
            else (
                duplicate_audit_advancement
                if duplicate_audit_advancement is not None
                else (duplicate_advancements or 0)
            )
        )
    )

    if auth_execs != 1:
        raise AssertionError(
            f"Expected exactly 1 authoritative execution, observed {auth_execs} "
            f"across {total_replays} replay attempts."
        )
    if provider_effects != 1:
        raise AssertionError(
            f"Expected exactly 1 provider side-effect, observed {provider_effects}."
        )
    if outcomes != 1:
        raise AssertionError(
            f"Expected exactly 1 terminal outcome advancement, observed {outcomes}."
        )
    if dup_adv != 0:
        raise AssertionError(f"Expected 0 duplicate advancements, observed {dup_adv}.")


def assert_terminal_state_preserved(result: AttackResult) -> None:
    """Assert that an illegal state transition was rejected and terminal state held."""
    assert_disposition_is_secure(result)
    if result.disposition not in (
        AttackDisposition.REJECTED,
        AttackDisposition.BLOCKED,
    ):
        raise AssertionError(
            f"Expected REJECTED or BLOCKED for illegal state transition, got {result.disposition}"
        )


def assert_truth_plane_isolated(result: AttackResult) -> None:
    """Assert that evaluator hidden truth did not leak to runtime decision authority."""
    assert_disposition_is_secure(result)
    if result.disposition not in (
        AttackDisposition.CONTAINED,
        AttackDisposition.DETECTED,
    ):
        raise AssertionError(
            f"Expected CONTAINED or DETECTED for truth-plane injection, got {result.disposition}"
        )


def assert_zero_truth_leakage(payload: dict[str, Any] | str) -> None:
    """Assert that oracle fields never appear in runtime payload or JSON serialization."""
    text_repr = json.dumps(payload) if isinstance(payload, dict) else str(payload)
    forbidden_truth_keys = [
        "oracle_action",
        "oracle_recovery_amount",
        "counterfactual_outcomes",
        "latent_probability",
    ]
    for key in forbidden_truth_keys:
        if f'"{key}"' in text_repr or f"'{key}'" in text_repr:
            raise AssertionError(
                f"Truth-plane contamination detected: '{key}' present in runtime artifact"
            )


def assert_audit_immutable(result: AttackResult) -> None:
    """Assert that audit tampering attempt was blocked or accurately detected."""
    assert_disposition_is_secure(result)
    if result.disposition not in (
        AttackDisposition.BLOCKED,
        AttackDisposition.DETECTED,
    ):
        raise AssertionError(
            f"Expected BLOCKED or DETECTED for audit tampering, got {result.disposition}"
        )


def assert_audit_immutability_enforced(
    attempted_updates: int,
    attempted_deletes: int,
    blocked_updates: int,
    blocked_deletes: int,
) -> None:
    """Assert that all attempted audit updates and deletes were blocked by PostgreSQL triggers."""
    if blocked_updates != attempted_updates or blocked_deletes != attempted_deletes:
        raise AssertionError(
            f"Audit immutability violation: updates blocked {blocked_updates}/{attempted_updates}, "
            f"deletes blocked {blocked_deletes}/{attempted_deletes}"
        )


def assert_reconstruction_detects_omission(trace: Any) -> None:
    """Assert that reconstruction trace surfaces missing lifecycle stages."""
    from apro.audit.enums import AuditCompleteness

    if trace.completeness != AuditCompleteness.INCOMPLETE:
        raise AssertionError(
            f"Reconstruction failed to detect omitted events, reported: {trace.completeness}"
        )


def assert_benchmark_immutable(result: AttackResult) -> None:
    """Assert that benchmark report tampering was rejected."""
    assert_disposition_is_secure(result)
    if result.disposition not in (
        AttackDisposition.BLOCKED,
        AttackDisposition.REJECTED,
    ):
        raise AssertionError(
            f"Expected BLOCKED or REJECTED for benchmark tampering, got {result.disposition}"
        )


def assert_benchmark_immutability_enforced(
    attempted_updates: int,
    attempted_deletes: int,
    blocked_updates: int,
    blocked_deletes: int,
) -> None:
    """Assert that all attempted benchmark report updates and deletes were blocked by PostgreSQL triggers."""
    if blocked_updates != attempted_updates or blocked_deletes != attempted_deletes:
        raise AssertionError(
            f"Benchmark immutability violation: updates blocked {blocked_updates}/{attempted_updates}, "
            f"deletes blocked {blocked_deletes}/{attempted_deletes}"
        )


def assert_dashboard_read_only(result: AttackResult) -> None:
    """Assert that dashboard API mutation attempt was blocked (HTTP 405)."""
    assert_disposition_is_secure(result)
    if result.disposition != AttackDisposition.BLOCKED:
        raise AssertionError(
            f"Expected BLOCKED for dashboard mutating request, got {result.disposition}"
        )


def assert_dashboard_read_only_enforced(
    attempted_mutations: int,
    blocked_mutations: int,
) -> None:
    """Assert that 100% of mutating HTTP requests to the dashboard API were rejected with 405."""
    if blocked_mutations != attempted_mutations or attempted_mutations == 0:
        raise AssertionError(
            f"Dashboard read-only violation: blocked {blocked_mutations}/{attempted_mutations} mutations"
        )


def assert_zero_secret_leakage(
    text_content: str | None = None,
    sentinels: list[str] | None = None,
    leaked_count: int = 0,
) -> None:
    """Assert that none of the target sentinels appear in text content or leak count is 0."""
    if leaked_count > 0:
        raise AssertionError(f"Sensitive sentinel token leaked: count={leaked_count}")
    if text_content is not None and sentinels is not None:
        for s in sentinels:
            if s in text_content:
                raise AssertionError(f"Sensitive sentinel token leaked: '{s}'")
