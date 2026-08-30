"""Unit tests for distribution shift benchmark evaluation (Phase 6)."""

from apro.evaluation.baselines import AlwaysRetryStrategy, NoInterventionStrategy
from apro.evaluation.benchmark import BenchmarkConfig, BenchmarkRunner
from apro.simulation.config import SimulationConfig
from apro.simulation.enums import (
    CustomerBehaviorClass,
    PaymentValueTier,
    RecoverabilityClass,
    ScenarioDifficulty,
    ScenarioFamily,
    SimulatedPaymentMethod,
)


def test_distribution_shift_benchmark_execution() -> None:
    """AC-10: Test benchmark on shifted simulator distribution."""
    # Shifted configuration with higher difficulty and altered distributions
    shifted_config = SimulationConfig(
        configuration_version="config-shift-v1",
        difficulty_distribution={
            ScenarioDifficulty.EASY: 0.10,
            ScenarioDifficulty.AMBIGUOUS: 0.30,
            ScenarioDifficulty.HARD: 0.40,
            ScenarioDifficulty.ADVERSARIAL: 0.20,
        },
        family_distribution={
            ScenarioFamily.TRANSIENT_FAILURE: 0.10,
            ScenarioFamily.BANK_SIDE_FAILURE: 0.20,
            ScenarioFamily.CUSTOMER_SIDE_FAILURE: 0.20,
            ScenarioFamily.AUTHENTICATION_FAILURE: 0.20,
            ScenarioFamily.PAYMENT_METHOD_FAILURE: 0.15,
            ScenarioFamily.GATEWAY_FAILURE: 0.05,
            ScenarioFamily.TIMEOUT: 0.05,
            ScenarioFamily.UNKNOWN_FAILURE: 0.05,
        },
        recoverability_distribution={
            RecoverabilityClass.HIGHLY_RECOVERABLE: 0.15,
            RecoverabilityClass.MODERATELY_RECOVERABLE: 0.25,
            RecoverabilityClass.LOW_RECOVERABILITY: 0.35,
            RecoverabilityClass.NON_RECOVERABLE: 0.25,
        },
        behavior_distribution={
            CustomerBehaviorClass.HIGHLY_RESPONSIVE: 0.10,
            CustomerBehaviorClass.NORMAL: 0.30,
            CustomerBehaviorClass.LOW_RESPONSIVENESS: 0.40,
            CustomerBehaviorClass.UNPREDICTABLE: 0.20,
        },
        value_tier_distribution={
            PaymentValueTier.LOW_VALUE: 0.20,
            PaymentValueTier.MEDIUM_VALUE: 0.50,
            PaymentValueTier.HIGH_VALUE: 0.30,
        },
        method_distribution={
            SimulatedPaymentMethod.UPI: 0.30,
            SimulatedPaymentMethod.CARD: 0.40,
            SimulatedPaymentMethod.NETBANKING: 0.20,
            SimulatedPaymentMethod.WALLET: 0.08,
            SimulatedPaymentMethod.OTHER_SUPPORTED_METHOD: 0.02,
        },
    )

    shift_name = "high_difficulty_heavy_bank_customer_failures"
    bench_config = BenchmarkConfig(
        benchmark_version="benchmark-shift-v1",
        dataset_version="dataset-shift-v1",
        target_case_count=100,
        seeds=[123, 456],
        simulation_config=shifted_config,
        distribution_shift_name=shift_name,
    )

    runner = BenchmarkRunner()
    dataset = runner.generate_benchmark_dataset(bench_config)

    assert dataset.manifest.benchmark_version == "benchmark-shift-v1"
    assert dataset.manifest.configuration_version == "config-shift-v1"
    assert dataset.manifest.metadata.get("distribution_shift_name") == shift_name

    result = runner.run_benchmark(
        dataset, [NoInterventionStrategy(), AlwaysRetryStrategy()]
    )
    assert result.manifest.distribution_shift_name == shift_name
    assert "Always Retry" in result.strategy_metrics
