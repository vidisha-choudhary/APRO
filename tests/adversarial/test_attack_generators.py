"""Unit tests for deterministic seed-based attack generators."""

from apro.adversarial.generators import (
    generate_all_attack_cases,
    generate_policy_bypass_cases,
    generate_replay_storm_cases,
)


def test_generator_determinism_under_fixed_seed() -> None:
    """Same seed generates identical attack IDs, payloads, and manifest hashes."""
    cases_run1 = generate_all_attack_cases(seed=1701)
    cases_run2 = generate_all_attack_cases(seed=1701)

    assert len(cases_run1) == 10
    assert len(cases_run2) == 10

    for sc_id in cases_run1:
        assert len(cases_run1[sc_id]) == len(cases_run2[sc_id])
        for c1, c2 in zip(cases_run1[sc_id], cases_run2[sc_id], strict=True):
            assert c1.attack_id == c2.attack_id
            assert c1.input_manifest_hash == c2.input_manifest_hash
            assert c1.input_payload == c2.input_payload


def test_generator_diversity_under_different_seeds() -> None:
    """Different seeds generate distinct attack IDs and manifest hashes."""
    cases_a = generate_policy_bypass_cases(seed=100)
    cases_b = generate_policy_bypass_cases(seed=200)

    assert cases_a[0].attack_id != cases_b[0].attack_id
    assert cases_a[0].input_manifest_hash != cases_b[0].input_manifest_hash


def test_replay_storm_generator_produces_50_cases() -> None:
    """Replay storm generator produces 50 distinct indexed cases sharing identical idempotency key."""
    cases = generate_replay_storm_cases(seed=1701, count=50)
    assert len(cases) == 50
    base_key = cases[0].input_payload["idempotency_key"]
    assert all(c.input_payload["idempotency_key"] == base_key for c in cases)
