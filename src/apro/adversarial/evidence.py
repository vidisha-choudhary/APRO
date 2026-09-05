"""Forensic evidence collection, sanitization, and SHA-256 manifest hashing."""

from typing import Any

from apro.adversarial.enums import ATTACK_SUITE_VERSION, CANONICAL_SENTINELS
from apro.adversarial.models import (
    AttackCase,
    AttackEvidence,
    AttackResult,
    AttackRun,
    compute_canonical_hash,
    get_current_code_revision,
)


def sanitize_adversarial_evidence(data: Any) -> Any:
    """Sanitize all data structures to ensure zero credentials, keys, or passwords leak."""
    if isinstance(data, dict):
        sanitized: dict[str, Any] = {}
        for k, v in data.items():
            if any(
                secret_key in k.lower()
                for secret_key in [
                    "secret",
                    "password",
                    "bearer",
                    "token",
                    "auth",
                    "key",
                    "card",
                ]
            ):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, str):
                val = v
                for sentinel in CANONICAL_SENTINELS:
                    val = val.replace(sentinel, "[REDACTED_SENTINEL]")
                sanitized[k] = val
            elif isinstance(v, dict | list):
                sanitized[k] = sanitize_adversarial_evidence(v)
            else:
                sanitized[k] = v
        return sanitized
    if isinstance(data, list):
        return [sanitize_adversarial_evidence(item) for item in data]
    if isinstance(data, str):
        val = data
        for sentinel in CANONICAL_SENTINELS:
            val = val.replace(sentinel, "[REDACTED_SENTINEL]")
        return val
    return data


def build_attack_manifest(
    attack_run_id: str,
    seed: int,
    cases: dict[str, list[AttackCase]],
    code_revision: str | None = None,
) -> AttackRun:
    """Construct an immutable AttackRun manifest with input hash."""
    rev = code_revision or get_current_code_revision()
    scenario_ids = sorted(cases.keys())
    cases_summary: list[dict[str, Any]] = []
    for sc_id in scenario_ids:
        for c in cases[sc_id]:
            cases_summary.append(
                {
                    "attack_id": c.attack_id,
                    "scenario_id": str(c.scenario_id),
                    "category": str(c.category),
                    "manifest_hash": c.input_manifest_hash,
                }
            )

    manifest_payload = {
        "attack_suite_version": ATTACK_SUITE_VERSION,
        "seed": seed,
        "scenario_ids": scenario_ids,
        "code_revision": rev,
        "cases": cases_summary,
    }
    input_manifest_hash = compute_canonical_hash(manifest_payload)

    return AttackRun(
        attack_run_id=attack_run_id,
        attack_suite_version=ATTACK_SUITE_VERSION,
        seed=seed,
        scenario_ids=scenario_ids,
        code_revision=rev,
        environment="isolated_local_test",
        input_manifest_hash=input_manifest_hash,
        evidence_hash="",
    )


def build_attack_evidence(
    attack_run_id: str,
    manifest_hash: str,
    scenario_results: dict[str, list[AttackResult]],
) -> AttackEvidence:
    """Aggregate sanitized results into an AttackEvidence artifact with canonical SHA-256 hash."""
    total = 0
    passed = 0
    failed = 0

    sanitized_results: dict[str, list[AttackResult]] = {}
    canonical_results_payload: dict[str, list[dict[str, Any]]] = {}

    for sc_id in sorted(scenario_results.keys()):
        sanitized_results[sc_id] = []
        canonical_results_payload[sc_id] = []
        for res in scenario_results[sc_id]:
            total += 1
            if res.passed:
                passed += 1
            else:
                failed += 1

            sanitized_evidence_dict = sanitize_adversarial_evidence(
                res.sanitized_evidence
            )
            clean_res = AttackResult.create(
                attack_id=res.attack_id,
                scenario_id=res.scenario_id,
                disposition=res.disposition,
                passed=res.passed,
                expected_property=res.expected_property,
                observed_property=res.observed_property,
                sanitized_evidence=sanitized_evidence_dict,
                exception_type=res.exception_type,
                executed_at=res.executed_at,
            )
            sanitized_results[sc_id].append(clean_res)
            canonical_results_payload[sc_id].append(
                {
                    "attack_id": clean_res.attack_id,
                    "scenario_id": str(clean_res.scenario_id),
                    "disposition": str(clean_res.disposition),
                    "passed": clean_res.passed,
                    "evidence_hash": clean_res.evidence_hash,
                }
            )

    evidence_payload = {
        "manifest_hash": manifest_hash,
        "total_attacks": total,
        "passed_attacks": passed,
        "failed_attacks": failed,
        "results": canonical_results_payload,
    }
    evidence_hash = compute_canonical_hash(evidence_payload)

    return AttackEvidence(
        attack_run_id=attack_run_id,
        scenario_results=sanitized_results,
        total_attacks=total,
        passed_attacks=passed,
        failed_attacks=failed,
        manifest_hash=manifest_hash,
        evidence_hash=evidence_hash,
    )
