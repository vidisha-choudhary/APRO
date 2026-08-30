"""Unit and integration tests for Model A distribution shift evaluation (Phase 7)."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.classifiers import (
    MultinomialLogisticRegressionDiagnosisModel,
)
from apro.diagnosis.evaluation import DiagnosisEvaluator
from apro.evaluation.benchmark import BenchmarkConfig, BenchmarkRunner
from apro.simulation.config import SimulationConfig


def test_distribution_shift_evaluation_workflow() -> None:
    """AC-20: Test evaluating Model A on in-distribution and shifted benchmarks."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-shift-v1", [1, 2], 30)

    model = MultinomialLogisticRegressionDiagnosisModel(max_iter=40)
    model.fit_on_dataset(train_ds)

    runner = BenchmarkRunner()
    # 1. In-distribution benchmark
    in_dist_config = BenchmarkConfig(
        benchmark_version="in-dist-v1",
        target_case_count=20,
        seeds=[42],
    )
    in_dist_ds = runner.generate_benchmark_dataset(in_dist_config)

    # 2. Shifted benchmark (high timeout & failure rate)
    shifted_sim_config = SimulationConfig(
        scenario_family_weights={
            "TRANSIENT_FAILURE": 0.05,
            "BANK_SIDE_FAILURE": 0.10,
            "CUSTOMER_SIDE_FAILURE": 0.05,
            "AUTHENTICATION_FAILURE": 0.10,
            "PAYMENT_METHOD_FAILURE": 0.05,
            "GATEWAY_FAILURE": 0.15,
            "TIMEOUT": 0.45,
            "UNKNOWN_FAILURE": 0.05,
        }
    )
    shifted_config = BenchmarkConfig(
        benchmark_version="shifted-v1",
        target_case_count=20,
        seeds=[42],
        simulation_config=shifted_sim_config,
        distribution_shift_name="high_timeout_stress",
    )
    shifted_ds = runner.generate_benchmark_dataset(shifted_config)

    evaluator = DiagnosisEvaluator()
    in_metrics, _ = evaluator.evaluate_model(model, in_dist_ds)
    shift_metrics, _ = evaluator.evaluate_model(model, shifted_ds)

    comparison = evaluator.compare_distribution_shift(in_metrics, shift_metrics)

    assert "in_distribution" in comparison
    assert "shifted_distribution" in comparison
    assert "deltas" in comparison
    assert "macro_f1_delta" in comparison["deltas"]
