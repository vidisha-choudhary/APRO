"""Frozen benchmark dataset execution and evaluation runner for APRO Phase 6."""

import json
import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.dataset.models import GovernedDataset
from apro.evaluation.aggregation import (
    MultiSeedStats,
    aggregate_by_segment,
    aggregate_multi_seed_metrics,
)
from apro.evaluation.baselines import BaseStrategy, NoInterventionStrategy
from apro.evaluation.metrics import (
    EvaluationMetrics,
    calculate_metrics,
)
from apro.evaluation.traces import CaseEvaluationTrace
from apro.simulation.config import SimulationConfig
from apro.simulation.engine import (
    OutcomeEngine,
    evaluate_action_outcome_from_probability,
)
from apro.simulation.enums import (
    CustomerBehaviorClass,
    PaymentValueTier,
    RecoverabilityClass,
    ScenarioDifficulty,
    ScenarioFamily,
    SimulatedActionType,
    SimulatedPaymentMethod,
)


def _zero_latency_recursive(obj: Any) -> None:
    """Recursively zero out latency fields for canonical comparison."""
    if isinstance(obj, dict):
        if "average_decision_latency_ms" in obj:
            obj["average_decision_latency_ms"] = 0.0
        if "decision_latency_ms" in obj:
            obj["decision_latency_ms"] = 0.0
        for v in obj.values():
            _zero_latency_recursive(v)
    elif isinstance(obj, list):
        for item in obj:
            _zero_latency_recursive(item)


class BenchmarkConfig(BaseModel):
    """Configuration governing benchmark generation and evaluation scope."""

    model_config = ConfigDict(frozen=True)

    benchmark_version: str = Field(default="benchmark-v1", min_length=1)
    dataset_version: str = Field(default="benchmark-dataset-v1", min_length=1)
    target_case_count: int = Field(default=1000, ge=10)
    seeds: list[int] = Field(default_factory=lambda: [42, 101, 2026])
    simulation_config: SimulationConfig = Field(default_factory=SimulationConfig)
    distribution_shift_name: str | None = None
    created_at: str | None = None


class BenchmarkManifest(BaseModel):
    """Immutable manifest recording benchmark execution provenance."""

    model_config = ConfigDict(frozen=True)

    benchmark_version: str
    dataset_version: str
    scenario_version: str
    configuration_version: str
    feature_schema_version: str
    seed_list: list[int]
    case_count: int = Field(ge=0)
    strategy_versions: dict[str, str]
    metric_version: str = Field(default="metric-v1")
    created_at: str
    distribution_shift_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkRunResult(BaseModel):
    """Consolidated output of benchmark execution across all strategies."""

    model_config = ConfigDict(frozen=True)

    manifest: BenchmarkManifest
    strategy_metrics: dict[str, EvaluationMetrics]
    strategy_seed_metrics: dict[str, dict[int, EvaluationMetrics]]
    strategy_multi_seed_stats: dict[str, dict[str, MultiSeedStats]]
    strategy_segment_metrics: dict[str, dict[str, dict[str, EvaluationMetrics]]]
    traces: dict[str, list[CaseEvaluationTrace]]
    coverage: dict[str, dict[str, int]]

    def to_canonical_dict(self) -> dict[str, Any]:
        """Return canonical deterministic dictionary for reproducible equality."""
        data = self.model_dump()
        _zero_latency_recursive(data)
        return data

    def to_canonical_json(self) -> str:
        """Return canonical deterministic JSON string."""
        return json.dumps(self.to_canonical_dict(), indent=2, sort_keys=True)


def get_payment_value_tier(amount: int, config: SimulationConfig) -> PaymentValueTier:
    """Determine payment value tier from amount and config."""
    for tier, (min_amt, max_amt) in config.amount_ranges.items():
        if min_amt <= amount <= max_amt:
            return tier
    if amount < config.amount_ranges[PaymentValueTier.LOW_VALUE][0]:
        return PaymentValueTier.LOW_VALUE
    return PaymentValueTier.HIGH_VALUE


class BenchmarkRunner:
    """Automated, deterministic benchmark execution and evaluation engine."""

    def __init__(self, outcome_engine: OutcomeEngine | None = None) -> None:
        self._outcome_engine = outcome_engine or OutcomeEngine()

    def generate_benchmark_dataset(self, config: BenchmarkConfig) -> GovernedDataset:
        """Generate a frozen benchmark dataset matching exact target count."""
        generator = DatasetGenerator(config.simulation_config)
        num_seeds = len(config.seeds)
        base_cases = config.target_case_count // num_seeds
        remainder = config.target_case_count % num_seeds

        # Exact deterministic remainder allocation (e.g. 334, 333, 333 -> 1000)
        cases_per_seed = [
            base_cases + (1 if idx < remainder else 0) for idx in range(num_seeds)
        ]

        return generator.generate_dataset(
            dataset_type=DatasetType.BENCHMARK,
            dataset_version=config.dataset_version,
            seeds=config.seeds,
            cases_per_seed=cases_per_seed,
            benchmark_version=config.benchmark_version,
            metadata={"distribution_shift_name": config.distribution_shift_name},
            created_at=config.created_at,
        )

    def evaluate_coverage(self, dataset: GovernedDataset) -> dict[str, dict[str, int]]:
        """Compute coverage distribution across all scenario dimensions."""
        coverage: dict[str, dict[str, int]] = {
            "scenario_family": {f.value: 0 for f in ScenarioFamily},
            "recoverability": {r.value: 0 for r in RecoverabilityClass},
            "customer_behavior": {b.value: 0 for b in CustomerBehaviorClass},
            "payment_method": {m.value: 0 for m in SimulatedPaymentMethod},
            "scenario_difficulty": {d.value: 0 for d in ScenarioDifficulty},
            "candidate_actions": {a.value: 0 for a in SimulatedActionType},
            "seeds": {},
        }

        for r in dataset.records:
            eval_t = r.evaluation_truth
            snap = r.model_input.features

            coverage["scenario_family"][eval_t.scenario_family.value] += 1
            coverage["recoverability"][eval_t.recoverability.value] += 1
            coverage["customer_behavior"][eval_t.customer_behavior.value] += 1
            coverage["payment_method"][snap.payment_method.value] += 1
            coverage["scenario_difficulty"][eval_t.scenario_difficulty.value] += 1

            for act in snap.candidate_actions:
                coverage["candidate_actions"][act.value] += 1

            s_key = str(r.model_input.generation_seed)
            coverage["seeds"][s_key] = coverage["seeds"].get(s_key, 0) + 1

        return coverage

    def run_benchmark(
        self,
        dataset: GovernedDataset,
        strategies: list[BaseStrategy],
        outcome_seed: int | None = None,
        baseline_for_incremental: str = "No Intervention",
        created_at: str | None = None,
    ) -> BenchmarkRunResult:
        """Run all strategies across benchmark dataset and compute metrics."""
        if not strategies:
            msg = "At least one strategy must be provided."
            raise ValueError(msg)

        sim_config = SimulationConfig()
        traces_by_strategy: dict[str, list[CaseEvaluationTrace]] = {}
        strategy_versions: dict[str, str] = {s.name: s.version for s in strategies}

        # 1. Run each strategy and record per-case evaluation traces
        for strategy in strategies:
            strat_traces: list[CaseEvaluationTrace] = []
            for record in dataset.records:
                model_input = record.model_input
                eval_truth = record.evaluation_truth
                snapshot = model_input.features

                # Time action selection latency
                t0 = time.perf_counter()
                chosen_action = strategy.select_action(model_input)
                t1 = time.perf_counter()
                latency_ms = (t1 - t0) * 1000.0

                # Validate chosen action is a legitimate candidate
                if chosen_action not in snapshot.candidate_actions:
                    chosen_action = SimulatedActionType.STOP

                # Causal Outcome Evaluation using simulator ground truth
                true_prob = eval_truth.true_action_probabilities.get(chosen_action, 0.0)
                sim_outcome = evaluate_action_outcome_from_probability(
                    true_prob=true_prob,
                    action=chosen_action,
                    amount=snapshot.payment_amount,
                    generation_seed=model_input.generation_seed,
                    scenario_id=model_input.scenario_id,
                    outcome_seed=outcome_seed,
                )

                recovered_amount = sim_outcome.recovered_amount
                best_val = eval_truth.best_achievable_value
                best_act = eval_truth.best_achievable_action
                regret = max(0, best_val - recovered_amount)
                is_opt = (chosen_action == best_act) or (
                    recovered_amount == best_val and best_val > 0
                )

                is_interv = chosen_action != SimulatedActionType.STOP
                # Unnecessary if intervention on non-recoverable
                is_unnecessary = is_interv and (
                    eval_truth.recoverability == RecoverabilityClass.NON_RECOVERABLE
                    or best_val == 0
                )

                val_tier = get_payment_value_tier(snapshot.payment_amount, sim_config)

                clean_sname = strategy.name.replace(" ", "_")
                trace = CaseEvaluationTrace(
                    case_id=f"case_{model_input.scenario_id}_{clean_sname}",
                    scenario_id=model_input.scenario_id,
                    strategy_name=strategy.name,
                    strategy_version=strategy.version,
                    dataset_version=model_input.dataset_version,
                    scenario_version=model_input.scenario_version,
                    configuration_version=model_input.configuration_version,
                    seed=model_input.generation_seed,
                    payment_amount=snapshot.payment_amount,
                    candidate_actions=snapshot.candidate_actions,
                    chosen_action=chosen_action,
                    outcome_status=sim_outcome.status,
                    recovered_amount=recovered_amount,
                    attempt_duration_seconds=sim_outcome.attempt_duration_seconds,
                    best_achievable_action=best_act,
                    best_achievable_value=best_val,
                    regret=regret,
                    is_optimal=is_opt,
                    is_intervention=is_interv,
                    is_unnecessary_intervention=is_unnecessary,
                    decision_latency_ms=latency_ms,
                    scenario_family=eval_truth.scenario_family,
                    recoverability=eval_truth.recoverability,
                    customer_behavior=eval_truth.customer_behavior,
                    scenario_difficulty=eval_truth.scenario_difficulty,
                    payment_value_tier=val_tier,
                )
                strat_traces.append(trace)

            traces_by_strategy[strategy.name] = strat_traces

        # 2. Determine baseline recovered revenue for incremental calculations
        baseline_traces = traces_by_strategy.get(
            baseline_for_incremental,
            traces_by_strategy.get(NoInterventionStrategy().name, []),
        )
        baseline_recovered = sum(t.recovered_amount for t in baseline_traces)

        # Baseline recovered by segment for segment incremental calculations
        baseline_seg_recovered: dict[str, dict[str, int]] = {}
        for dim in [
            "scenario_family",
            "recoverability",
            "customer_behavior",
            "payment_value_tier",
            "scenario_difficulty",
        ]:
            seg_metrics = aggregate_by_segment(baseline_traces, dim)
            baseline_seg_recovered[dim] = {
                k: m.economic.revenue_recovered for k, m in seg_metrics.items()
            }

        # 3. Compute Metrics and Multi-Seed Aggregations
        strategy_metrics: dict[str, EvaluationMetrics] = {}
        strategy_seed_metrics: dict[str, dict[int, EvaluationMetrics]] = {}
        strategy_multi_seed_stats: dict[str, dict[str, MultiSeedStats]] = {}
        strategy_segment_metrics: dict[
            str, dict[str, dict[str, EvaluationMetrics]]
        ] = {}

        for strategy_name, traces in traces_by_strategy.items():
            # Overall metric
            strategy_metrics[strategy_name] = calculate_metrics(
                traces, baseline_revenue_recovered=baseline_recovered
            )

            # Per-seed metrics
            seed_map: dict[int, list[CaseEvaluationTrace]] = {}
            for t in traces:
                seed_map.setdefault(t.seed, []).append(t)

            per_seed_m: dict[int, EvaluationMetrics] = {}
            for s, s_traces in seed_map.items():
                per_seed_m[s] = calculate_metrics(
                    s_traces, baseline_revenue_recovered=0
                )
            strategy_seed_metrics[strategy_name] = per_seed_m

            # Multi-seed statistics
            strategy_multi_seed_stats[strategy_name] = aggregate_multi_seed_metrics(
                per_seed_m
            )

            # Segment metrics
            seg_results: dict[str, dict[str, EvaluationMetrics]] = {}
            for dim in [
                "scenario_family",
                "recoverability",
                "customer_behavior",
                "payment_value_tier",
                "scenario_difficulty",
            ]:
                seg_results[dim] = aggregate_by_segment(
                    traces,
                    dim,
                    baseline_recovered_by_segment=baseline_seg_recovered.get(dim),
                )
            strategy_segment_metrics[strategy_name] = seg_results

        # 4. Construct Benchmark Manifest and Result
        coverage = self.evaluate_coverage(dataset)
        manifest_time = (
            created_at or dataset.manifest.created_at or datetime.now(UTC).isoformat()
        )
        manifest = BenchmarkManifest(
            benchmark_version=(dataset.manifest.benchmark_version or "benchmark-v1"),
            dataset_version=dataset.manifest.dataset_version,
            scenario_version=dataset.manifest.scenario_version,
            configuration_version=dataset.manifest.configuration_version,
            feature_schema_version=dataset.manifest.feature_schema_version,
            seed_list=dataset.manifest.seed_list,
            case_count=len(dataset.records),
            strategy_versions=strategy_versions,
            created_at=manifest_time,
            distribution_shift_name=dataset.manifest.metadata.get(
                "distribution_shift_name"
            ),
        )

        return BenchmarkRunResult(
            manifest=manifest,
            strategy_metrics=strategy_metrics,
            strategy_seed_metrics=strategy_seed_metrics,
            strategy_multi_seed_stats=strategy_multi_seed_stats,
            strategy_segment_metrics=strategy_segment_metrics,
            traces=traces_by_strategy,
            coverage=coverage,
        )
