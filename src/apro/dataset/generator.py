"""Deterministic dataset generator for APRO Phase 6."""

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from apro.dataset.enums import DatasetType
from apro.dataset.feature_snapshot import create_feature_snapshot
from apro.dataset.leakage_checks import (
    validate_feature_snapshot,
    validate_model_input_record,
)
from apro.dataset.models import (
    DatasetManifest,
    DatasetRecord,
    EvaluationTruthRecord,
    GovernedDataset,
    ModelInputRecord,
    TrainingObservation,
)
from apro.simulation.config import SimulationConfig
from apro.simulation.engine import evaluate_action_outcome_from_probability
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedOutcomeStatus,
)
from apro.simulation.generator import ScenarioGenerator
from apro.simulation.models import SimulationScenario


def determine_best_achievable_action_and_value(
    scenario: SimulationScenario,
) -> tuple[SimulatedActionType, int]:
    """Calculate the best achievable action and recovered value from ground truth."""
    amount = scenario.observable_state.payment.amount
    potential = scenario.hidden_state.potential_outcomes
    probs = scenario.hidden_state.true_action_probabilities

    successful_actions = [
        act
        for act in scenario.observable_state.candidate_actions
        if potential.get(act) == SimulatedOutcomeStatus.SUCCESS
    ]

    if not successful_actions:
        return SimulatedActionType.STOP, 0

    # Tie-breaking action priority (lower intervention cost / directness first)
    action_priority: dict[SimulatedActionType, int] = {
        SimulatedActionType.RETRY: 4,
        SimulatedActionType.PAYMENT_LINK: 3,
        SimulatedActionType.OUTREACH: 2,
        SimulatedActionType.ESCALATE: 1,
        SimulatedActionType.STOP: 0,
    }

    # Best action has highest true probability, broken by priority
    best_action = max(
        successful_actions,
        key=lambda a: (probs.get(a, 0.0), action_priority.get(a, 0)),
    )
    return best_action, amount


class DatasetGenerator:
    """Generates governed datasets with model-facing and truth separation."""

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self._config = config or SimulationConfig()
        self._scenario_generator = ScenarioGenerator(self._config)

    @property
    def config(self) -> SimulationConfig:
        return self._config

    def generate_dataset(
        self,
        dataset_type: DatasetType,
        dataset_version: str,
        seeds: list[int],
        cases_per_seed: int | list[int] | dict[int, int],
        benchmark_version: str | None = None,
        base_timestamp: datetime | None = None,
        time_step_seconds: int = 60,
        metadata: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> GovernedDataset:
        """Generate a reproducible dataset across specified seeds and case counts."""
        if not seeds:
            msg = "At least one seed must be provided to generate a dataset."
            raise ValueError(msg)

        # Normalize cases_per_seed map
        seed_cases: dict[int, int] = {}
        if isinstance(cases_per_seed, int):
            if cases_per_seed <= 0:
                msg = f"cases_per_seed must be positive (got {cases_per_seed})."
                raise ValueError(msg)
            seed_cases = dict.fromkeys(seeds, cases_per_seed)
        elif isinstance(cases_per_seed, list):
            if len(cases_per_seed) != len(seeds):
                msg = (
                    f"cases_per_seed list length ({len(cases_per_seed)}) "
                    f"must match seeds length ({len(seeds)})."
                )
                raise ValueError(msg)
            seed_cases = dict(zip(seeds, cases_per_seed, strict=True))
        elif isinstance(cases_per_seed, dict):
            for s in seeds:
                if s not in cases_per_seed:
                    msg = f"Seed {s} missing from cases_per_seed dict."
                    raise ValueError(msg)
            seed_cases = {s: cases_per_seed[s] for s in seeds}

        start_time = base_timestamp or datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        records: list[DatasetRecord] = []
        global_case_idx = 0

        for seed in seeds:
            num_cases = seed_cases[seed]
            for i in range(num_cases):
                # Derive deterministic case sub-seed
                case_seed = seed * 100000 + i
                scenario = self._scenario_generator.generate(seed=case_seed)

                # Deterministic decision timestamp
                decision_time = start_time + timedelta(
                    seconds=global_case_idx * time_step_seconds
                )
                global_case_idx += 1

                # 1. Decision-time Feature Snapshot
                snapshot = create_feature_snapshot(
                    observable_state=scenario.observable_state,
                    decision_timestamp=decision_time,
                    schema_version="feature-schema-v1",
                )
                validate_feature_snapshot(snapshot)

                record_id = f"rec_{scenario.scenario_id}"

                # 2. Model Input Record & Historical Training Observation
                training_label: TrainingObservation | None = None
                if dataset_type == DatasetType.TRAINING:
                    # Deterministic historical observation for training
                    hist_rng = random.Random(case_seed + 999)
                    candidates = scenario.observable_state.candidate_actions
                    observed_action = hist_rng.choice(candidates)
                    true_prob = scenario.hidden_state.true_action_probabilities.get(
                        observed_action, 0.0
                    )
                    hist_outcome = evaluate_action_outcome_from_probability(
                        true_prob=true_prob,
                        action=observed_action,
                        amount=scenario.observable_state.payment.amount,
                        generation_seed=case_seed,
                        scenario_id=scenario.scenario_id,
                        outcome_seed=None,
                    )
                    training_label = TrainingObservation(
                        observed_action=observed_action,
                        observed_outcome_status=hist_outcome.status,
                        recovered_amount=hist_outcome.recovered_amount,
                    )

                model_input = ModelInputRecord(
                    record_id=record_id,
                    dataset_type=dataset_type,
                    dataset_version=dataset_version,
                    scenario_id=scenario.scenario_id,
                    generation_seed=case_seed,
                    scenario_version=scenario.scenario_version,
                    configuration_version=scenario.configuration_version,
                    feature_schema_version=snapshot.feature_schema_version,
                    benchmark_version=benchmark_version,
                    features=snapshot,
                    training_label=training_label,
                )
                validate_model_input_record(model_input)

                # 3. Evaluation Truth Record
                best_act, best_val = determine_best_achievable_action_and_value(
                    scenario
                )
                eval_truth = EvaluationTruthRecord(
                    record_id=record_id,
                    scenario_id=scenario.scenario_id,
                    scenario_family=scenario.scenario_family,
                    recoverability=scenario.hidden_state.recoverability,
                    customer_behavior=scenario.hidden_state.customer_behavior,
                    true_failure_mechanism=scenario.hidden_state.true_failure_mechanism,
                    latent_customer_intent=scenario.hidden_state.latent_customer_intent,
                    latent_bank_condition=scenario.hidden_state.latent_bank_condition,
                    scenario_difficulty=scenario.hidden_state.scenario_difficulty,
                    true_action_probabilities=dict(
                        scenario.hidden_state.true_action_probabilities
                    ),
                    potential_outcomes=dict(scenario.hidden_state.potential_outcomes),
                    best_achievable_action=best_act,
                    best_achievable_value=best_val,
                )

                records.append(
                    DatasetRecord(
                        model_input=model_input,
                        evaluation_truth=eval_truth,
                    )
                )

        manifest = DatasetManifest(
            dataset_version=dataset_version,
            dataset_type=dataset_type,
            scenario_version=self._config.scenario_version,
            configuration_version=self._config.configuration_version,
            feature_schema_version="feature-schema-v1",
            benchmark_version=benchmark_version,
            seed_list=list(seeds),
            record_count=len(records),
            created_at=created_at or start_time.isoformat(),
            metadata=metadata or {},
        )

        return GovernedDataset(
            manifest=manifest,
            records=tuple(records),
        )
