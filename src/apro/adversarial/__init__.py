"""APRO Phase 17 — Adversarial Security & Attack Harness Package."""

from apro.adversarial.assertions import (
    assert_action_unauthorized,
    assert_audit_immutable,
    assert_benchmark_immutable,
    assert_dashboard_read_only,
    assert_disposition_is_secure,
    assert_exactly_once_advancement,
    assert_stale_authority_rejected,
    assert_terminal_state_preserved,
    assert_truth_plane_isolated,
    assert_zero_secret_leakage,
)
from apro.adversarial.enums import (
    ATTACK_SUITE_VERSION,
    CANONICAL_SENTINELS,
    AttackCategory,
    AttackDisposition,
    ScenarioId,
    Severity,
)
from apro.adversarial.evidence import (
    build_attack_evidence,
    build_attack_manifest,
    sanitize_adversarial_evidence,
)
from apro.adversarial.executor import AdversarialAttackExecutor
from apro.adversarial.generators import (
    generate_all_attack_cases,
    generate_audit_tampering_cases,
    generate_benchmark_tampering_cases,
    generate_capture_race_cases,
    generate_dashboard_abuse_cases,
    generate_illegal_state_cases,
    generate_policy_bypass_cases,
    generate_replay_storm_cases,
    generate_secret_exfiltration_cases,
    generate_stale_authority_cases,
    generate_truth_plane_cases,
)
from apro.adversarial.models import (
    AttackCase,
    AttackEvidence,
    AttackResult,
    AttackRun,
    compute_canonical_hash,
)
from apro.adversarial.replay import ReplayCoordinator
from apro.adversarial.scenarios import SCENARIO_REGISTRY, ScenarioDefinition

__all__ = [
    "ATTACK_SUITE_VERSION",
    "CANONICAL_SENTINELS",
    "AdversarialAttackExecutor",
    "AttackCase",
    "AttackCategory",
    "AttackDisposition",
    "AttackEvidence",
    "AttackResult",
    "AttackRun",
    "ReplayCoordinator",
    "SCENARIO_REGISTRY",
    "ScenarioDefinition",
    "ScenarioId",
    "Severity",
    "assert_action_unauthorized",
    "assert_audit_immutable",
    "assert_benchmark_immutable",
    "assert_dashboard_read_only",
    "assert_disposition_is_secure",
    "assert_exactly_once_advancement",
    "assert_stale_authority_rejected",
    "assert_terminal_state_preserved",
    "assert_truth_plane_isolated",
    "assert_zero_secret_leakage",
    "build_attack_evidence",
    "build_attack_manifest",
    "compute_canonical_hash",
    "generate_all_attack_cases",
    "generate_audit_tampering_cases",
    "generate_benchmark_tampering_cases",
    "generate_capture_race_cases",
    "generate_dashboard_abuse_cases",
    "generate_illegal_state_cases",
    "generate_policy_bypass_cases",
    "generate_replay_storm_cases",
    "generate_secret_exfiltration_cases",
    "generate_stale_authority_cases",
    "generate_truth_plane_cases",
    "sanitize_adversarial_evidence",
]
