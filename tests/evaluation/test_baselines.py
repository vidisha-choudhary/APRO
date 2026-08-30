"""Unit tests for baseline strategy adapters (Phase 6)."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.evaluation.baselines import (
    AlwaysRetryStrategy,
    GlobalActionRateStrategy,
    NoInterventionStrategy,
    StaticRulesStrategy,
)
from apro.simulation.enums import SimulatedActionType


def test_no_intervention_strategy() -> None:
    """AC-12, AC-13: Test No Intervention always returns STOP."""
    strat = NoInterventionStrategy()
    assert strat.name == "No Intervention"
    assert strat.version == "v1.0"

    gen = DatasetGenerator()
    dataset = gen.generate_dataset(DatasetType.BENCHMARK, "v1", [42], 5)

    for rec in dataset.records:
        action = strat.select_action(rec.model_input)
        assert action == SimulatedActionType.STOP


def test_always_retry_strategy() -> None:
    """AC-12, AC-13: Test Always Retry selects RETRY when available."""
    strat = AlwaysRetryStrategy()
    assert strat.name == "Always Retry"
    assert strat.version == "v1.0"

    gen = DatasetGenerator()
    dataset = gen.generate_dataset(DatasetType.BENCHMARK, "v1", [42], 5)

    for rec in dataset.records:
        action = strat.select_action(rec.model_input)
        if SimulatedActionType.RETRY in rec.model_input.features.candidate_actions:
            assert action == SimulatedActionType.RETRY
        else:
            assert action == SimulatedActionType.STOP


def test_static_rules_strategy() -> None:
    """AC-12, AC-13: Test Static Rules strategy maps failure codes deterministically."""
    strat = StaticRulesStrategy()
    assert strat.name == "Static Failure Rules"
    assert strat.version == "v1.0"

    gen = DatasetGenerator()
    dataset = gen.generate_dataset(DatasetType.BENCHMARK, "v1", [101], 20)

    for rec in dataset.records:
        action = strat.select_action(rec.model_input)
        assert action in rec.model_input.features.candidate_actions
        assert isinstance(action, SimulatedActionType)


def test_unfitted_global_action_rate_strategy_raises_error() -> None:
    """Correction 2 & 4: Unfitted strategy raises ValueError on select_action."""
    strat = GlobalActionRateStrategy()
    assert not strat.is_fitted

    gen = DatasetGenerator()
    test_ds = gen.generate_dataset(DatasetType.BENCHMARK, "bench-v1", [99], 1)
    rec = test_ds.records[0]

    with pytest.raises(ValueError, match="GlobalActionRateStrategy is unfitted"):
        strat.select_action(rec.model_input)


def test_global_action_rate_strategy_training_fitting() -> None:
    """Correction B & 3: Global Action Rate fits from typed TrainingObservations."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-v1", [1, 2], 20)
    test_ds = gen.generate_dataset(DatasetType.BENCHMARK, "bench-v1", [99], 10)

    strat = GlobalActionRateStrategy()
    assert not strat.is_fitted

    # Fit empirical rates from legitimate training data observations
    strat.fit(train_ds)
    assert strat.is_fitted

    for rec in test_ds.records:
        action = strat.select_action(rec.model_input)
        assert action in rec.model_input.features.candidate_actions


def test_global_action_rate_strategy_held_out_protection() -> None:
    """Correction C: Test Global Action Rate rejects non-TRAINING datasets."""
    gen = DatasetGenerator()
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-v1", [1], 5)
    test_ds = gen.generate_dataset(DatasetType.HELD_OUT_TEST, "test-v1", [2], 5)
    bench_ds = gen.generate_dataset(DatasetType.BENCHMARK, "bench-v1", [3], 5)

    strat = GlobalActionRateStrategy()

    with pytest.raises(ValueError, match="strictly permitted on TRAINING datasets"):
        strat.fit(val_ds)

    with pytest.raises(ValueError, match="strictly permitted on TRAINING datasets"):
        strat.fit(test_ds)

    with pytest.raises(ValueError, match="strictly permitted on TRAINING datasets"):
        strat.fit(bench_ds)
