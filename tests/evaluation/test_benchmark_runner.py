"""Unit and integration tests for BenchmarkRunner (Phase 6)."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.evaluation.baselines import (
    AlwaysRetryStrategy,
    GlobalActionRateStrategy,
    NoInterventionStrategy,
    StaticRulesStrategy,
)
from apro.evaluation.benchmark import BenchmarkConfig, BenchmarkRunner


def test_benchmark_runner_1000_cases_three_seeds() -> None:
    """Correction A, AC-09: Test exact 1,000-case 3-seed benchmark execution."""
    generator = DatasetGenerator()
    runner = BenchmarkRunner()
    config = BenchmarkConfig(
        benchmark_version="benchmark-v1",
        dataset_version="benchmark-dataset-v1",
        target_case_count=1000,
        seeds=[42, 101, 2026],
    )

    # 1. Fit Global Action Rate from legitimate TRAINING dataset
    train_dataset = generator.generate_dataset(
        dataset_type=DatasetType.TRAINING,
        dataset_version="train-baseline-v1",
        seeds=[1, 2],
        cases_per_seed=50,
    )
    gar_strat = GlobalActionRateStrategy()
    gar_strat.fit(train_dataset)

    # 2. Generate frozen benchmark dataset
    dataset = runner.generate_benchmark_dataset(config)
    assert len(dataset) == 1000
    assert dataset.manifest.record_count == 1000
    assert dataset.manifest.benchmark_version == "benchmark-v1"
    assert dataset.manifest.seed_list == [42, 101, 2026]

    # 3. Run benchmark across baseline strategies
    strategies = [
        NoInterventionStrategy(),
        AlwaysRetryStrategy(),
        StaticRulesStrategy(),
        gar_strat,
    ]
    result = runner.run_benchmark(dataset, strategies)

    # Verify manifest
    assert result.manifest.benchmark_version == "benchmark-v1"
    assert result.manifest.case_count == 1000
    assert len(result.manifest.strategy_versions) == 4

    # Verify each strategy evaluated on all 1,000 cases
    for strat in strategies:
        assert strat.name in result.strategy_metrics
        m = result.strategy_metrics[strat.name]
        assert m.case_count == 1000
        assert m.economic.revenue_at_risk > 0
        assert len(result.traces[strat.name]) == 1000

        # Multi-seed stats
        assert strat.name in result.strategy_multi_seed_stats
        stats = result.strategy_multi_seed_stats[strat.name]
        assert "recovery_rate" in stats
        assert "incremental_revenue_recovered" in stats
        assert stats["recovery_rate"].ci_95_lower <= stats["recovery_rate"].ci_95_upper

    # Check baseline performance relationships
    no_int = result.strategy_metrics["No Intervention"]
    assert no_int.economic.revenue_recovered == 0
    assert no_int.economic.recovery_rate == 0.0
    assert no_int.economic.intervention_count == 0
    assert no_int.economic.incremental_revenue_recovered == 0

    always_retry = result.strategy_metrics["Always Retry"]
    assert always_retry.economic.revenue_recovered > 0
    assert always_retry.economic.recovery_rate > 0.0
    assert always_retry.economic.incremental_revenue_recovered > 0


def test_benchmark_runner_unfitted_global_action_rate_raises_error() -> None:
    """Correction 4: Runner raises ValueError if unfitted baseline is passed."""
    runner = BenchmarkRunner()
    config = BenchmarkConfig(
        benchmark_version="benchmark-v1",
        dataset_version="benchmark-dataset-v1",
        target_case_count=10,
        seeds=[42],
    )
    dataset = runner.generate_benchmark_dataset(config)
    unfitted_strat = GlobalActionRateStrategy()

    with pytest.raises(ValueError, match="GlobalActionRateStrategy is unfitted"):
        runner.run_benchmark(dataset, [unfitted_strat])


def test_benchmark_runner_deterministic_canonical_reproducibility() -> None:
    """Correction F, AC-20: Test running benchmark twice reproduces canonical JSON."""
    runner = BenchmarkRunner()
    config = BenchmarkConfig(
        benchmark_version="benchmark-v1",
        dataset_version="benchmark-dataset-v1",
        target_case_count=100,
        seeds=[42, 101],
        created_at="2026-01-01T00:00:00+00:00",
    )

    dataset_1 = runner.generate_benchmark_dataset(config)
    dataset_2 = runner.generate_benchmark_dataset(config)

    strategies = [NoInterventionStrategy(), AlwaysRetryStrategy()]
    res_1 = runner.run_benchmark(
        dataset_1, strategies, created_at="2026-01-01T00:00:00+00:00"
    )
    res_2 = runner.run_benchmark(
        dataset_2, strategies, created_at="2026-01-01T00:00:00+00:00"
    )

    # Byte-for-byte canonical equality
    assert res_1.to_canonical_json() == res_2.to_canonical_json()
