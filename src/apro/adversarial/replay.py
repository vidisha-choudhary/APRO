"""Deterministic replay engine for reproducing adversarial attack runs."""

from apro.adversarial.evidence import build_attack_evidence, build_attack_manifest
from apro.adversarial.executor import AdversarialAttackExecutor
from apro.adversarial.generators import generate_all_attack_cases
from apro.adversarial.models import AttackEvidence, AttackResult, AttackRun


class ReplayCoordinator:
    """Orchestrates deterministic replay of adversarial test runs."""

    def __init__(self, executor: AdversarialAttackExecutor) -> None:
        self.executor = executor

    async def execute_run(
        self, seed: int, attack_run_id: str | None = None
    ) -> tuple[AttackRun, AttackEvidence]:
        """Execute a full deterministic attack run for all 10 scenarios."""
        run_id = attack_run_id or f"run_adv_{seed}_{1701}"
        cases_by_scenario = generate_all_attack_cases(seed)

        # Build input manifest
        manifest_dict = {str(k): v for k, v in cases_by_scenario.items()}
        manifest = build_attack_manifest(
            attack_run_id=run_id, seed=seed, cases=manifest_dict
        )

        results_by_scenario: dict[str, list[AttackResult]] = {}
        for scenario_id, cases in cases_by_scenario.items():
            sc_key = str(scenario_id)
            results_by_scenario[sc_key] = []
            for c in cases:
                res = await self.executor.execute_case(c)
                results_by_scenario[sc_key].append(res)

        evidence = build_attack_evidence(
            attack_run_id=run_id,
            manifest_hash=manifest.input_manifest_hash,
            scenario_results=results_by_scenario,
        )

        final_manifest = AttackRun(
            attack_run_id=manifest.attack_run_id,
            attack_suite_version=manifest.attack_suite_version,
            seed=manifest.seed,
            scenario_ids=manifest.scenario_ids,
            code_revision=manifest.code_revision,
            environment=manifest.environment,
            input_manifest_hash=manifest.input_manifest_hash,
            evidence_hash=evidence.evidence_hash,
            created_at=manifest.created_at,
        )

        return final_manifest, evidence

    async def verify_reproducibility(self, seed: int) -> bool:
        """Verify that running with identical seed produces identical evidence hashes."""
        run1, ev1 = await self.execute_run(seed=seed, attack_run_id=f"rep1_{seed}")
        run2, ev2 = await self.execute_run(seed=seed, attack_run_id=f"rep2_{seed}")

        return bool(
            run1.input_manifest_hash == run2.input_manifest_hash
            and ev1.evidence_hash == ev2.evidence_hash
            and ev1.total_attacks == ev2.total_attacks
            and ev1.passed_attacks == ev2.passed_attacks
            and ev1.failed_attacks == ev2.failed_attacks
        )
