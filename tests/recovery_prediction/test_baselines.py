"""Unit tests for Phase 8 recovery outcome baseline models."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.recovery_prediction.baselines import (
    ActionStratifiedHistoricalBaseline,
    GlobalActionRateBaseline,
    SimpleStatisticalOutcomeBaseline,
    StaticOutcomeRuleBaseline,
)
from apro.recovery_prediction.enums import RecoveryAction


def test_global_action_rate_baseline() -> None:
    """AC-09: Test Global Action Rate Baseline fitting and prediction."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-gar-v1", [42], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-gar-v1", [101], 10)

    model = GlobalActionRateBaseline()
    assert not model.is_fitted

    # Unfitted predict raises ValueError
    with pytest.raises(ValueError, match="is unfitted"):
        model.predict(val_ds.records[0].model_input, RecoveryAction.RETRY)

    model.fit_on_dataset(train_ds)
    assert model.is_fitted

    for rec in val_ds.records:
        pred_retry = model.predict(rec.model_input, RecoveryAction.RETRY)
        pred_stop = model.predict(rec.model_input, RecoveryAction.STOP)

        assert 0.0 <= pred_retry.predicted_success_probability <= 1.0
        assert pred_stop.predicted_success_probability == 0.0
        assert pred_stop.predicted_recovered_amount == 0


def test_action_stratified_historical_baseline() -> None:
    """AC-09: Test Action Stratified Historical Baseline."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-strat-v1", [42], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-strat-v1", [101], 10)

    model = ActionStratifiedHistoricalBaseline()
    model.fit_on_dataset(train_ds)
    assert model.is_fitted

    for rec in val_ds.records:
        for act in (RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK):
            pred = model.predict(rec.model_input, act)
            assert 0.0 <= pred.predicted_success_probability <= 1.0
            assert (
                0
                <= pred.predicted_recovered_amount
                <= rec.model_input.features.payment_amount
            )


def test_static_outcome_rule_baseline() -> None:
    """AC-09: Test Static Outcome Rule Baseline deterministic predictions."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-rule-v1", [42], 20)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-rule-v1", [101], 10)

    model = StaticOutcomeRuleBaseline()
    model.fit_on_dataset(train_ds)
    assert model.is_fitted

    for rec in val_ds.records:
        pred_stop = model.predict(rec.model_input, RecoveryAction.STOP)
        assert pred_stop.predicted_success_probability == 0.0
        assert pred_stop.predicted_recovered_amount == 0

        pred_retry = model.predict(rec.model_input, RecoveryAction.RETRY)
        assert 0.0 <= pred_retry.predicted_success_probability <= 1.0


def test_simple_statistical_outcome_baseline() -> None:
    """AC-09: Test Simple Statistical Outcome Baseline."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-stat-v1", [1, 2], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-stat-v1", [3], 10)

    model = SimpleStatisticalOutcomeBaseline()
    model.fit_on_dataset(train_ds)

    for rec in val_ds.records:
        pred = model.predict(rec.model_input, RecoveryAction.PAYMENT_LINK)
        assert 0.0 <= pred.predicted_success_probability <= 1.0
        assert (
            0
            <= pred.predicted_recovered_amount
            <= rec.model_input.features.payment_amount
        )
