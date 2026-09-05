"""Tests for Adversarial Replay Reproducibility and Hash Stability."""

import pytest

from apro.adversarial.executor import AdversarialAttackExecutor
from apro.adversarial.replay import ReplayCoordinator


@pytest.mark.asyncio
async def test_replay_coordinator_reproducibility(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """ReplayCoordinator executes identical attack cases twice and verifies 100% hash and outcome match."""
    coordinator = ReplayCoordinator(executor=adversarial_executor)

    run_1, ev_1 = await coordinator.execute_run(seed=1701, attack_run_id="run_rep_01")
    run_2, ev_2 = await coordinator.execute_run(seed=1701, attack_run_id="run_rep_02")

    assert run_1.input_manifest_hash == run_2.input_manifest_hash
    assert ev_1.evidence_hash == ev_2.evidence_hash
    assert ev_1.total_attacks == ev_2.total_attacks
    assert ev_1.passed_attacks == ev_2.passed_attacks
    assert ev_1.failed_attacks == ev_2.failed_attacks == 0
    assert await coordinator.verify_reproducibility(seed=1701) is True


@pytest.mark.asyncio
async def test_replay_coordinator_negative_sensitivity(
    adversarial_executor: AdversarialAttackExecutor,
) -> None:
    """Negative sensitivity test: different seed or tampered result produces different hashes."""
    from apro.adversarial.evidence import build_attack_evidence
    from apro.adversarial.models import AttackDisposition, AttackResult

    coordinator = ReplayCoordinator(executor=adversarial_executor)

    run_1, ev_1 = await coordinator.execute_run(seed=1701, attack_run_id="run_sens_01")
    run_diff_seed, ev_diff_seed = await coordinator.execute_run(
        seed=9999, attack_run_id="run_sens_02"
    )

    # Different seeds must produce different manifest hashes and evidence hashes
    assert run_1.input_manifest_hash != run_diff_seed.input_manifest_hash
    assert ev_1.evidence_hash != ev_diff_seed.evidence_hash

    # Tampering with a single result in scenario_results alters evidence_hash
    tampered_results = {k: list(v) for k, v in ev_1.scenario_results.items()}
    first_sc = sorted(tampered_results.keys())[0]
    first_res = tampered_results[first_sc][0]
    mutated_res = AttackResult.create(
        attack_id=first_res.attack_id,
        scenario_id=first_res.scenario_id,
        disposition=AttackDisposition.UNEXPECTED_SUCCESS,
        passed=False,
        expected_property=first_res.expected_property,
        observed_property="tampered result for sensitivity test",
        sanitized_evidence={"tampered": True},
    )
    tampered_results[first_sc][0] = mutated_res

    ev_tampered = build_attack_evidence(
        attack_run_id="run_tampered",
        manifest_hash=ev_1.manifest_hash,
        scenario_results=tampered_results,
    )
    assert ev_tampered.evidence_hash != ev_1.evidence_hash
