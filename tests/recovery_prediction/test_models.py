"""Unit tests for Phase 8 Model B outcome prediction classifiers."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.recovery_prediction.classifiers import (
    DecisionTreeOutcomeModel,
    LogisticRegressionOutcomeModel,
    RandomForestOutcomeModel,
)
from apro.recovery_prediction.enums import (
    PredictedOutcomeState,
    PredictionUncertaintyState,
    RecoveryAction,
)


def test_logistic_regression_outcome_model() -> None:
    """AC-10: Test Logistic Regression Model B training and prediction."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-lr-b-v1", [42], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-lr-b-v1", [101], 10)

    model = LogisticRegressionOutcomeModel(max_iter=30, seed=42)
    assert not model.is_fitted

    with pytest.raises(ValueError, match="is unfitted"):
        model.predict(val_ds.records[0].model_input, RecoveryAction.RETRY)

    model.fit_on_dataset(train_ds)
    assert model.is_fitted
    assert len(model.coefficients) > 0

    for rec in val_ds.records:
        multi_pred = model.predict_all_actions(rec.model_input)
        assert len(multi_pred.predictions) == 5

        pred_retry = multi_pred.predictions[RecoveryAction.RETRY]
        assert 0.0 <= pred_retry.predicted_success_probability <= 1.0
        assert pred_retry.predicted_outcome_state in (
            PredictedOutcomeState.SUCCESS,
            PredictedOutcomeState.FAILURE,
        )
        assert (
            0
            <= pred_retry.predicted_recovered_amount
            <= rec.model_input.features.payment_amount
        )


def test_decision_tree_outcome_model() -> None:
    """AC-11: Test Decision Tree Model B training and prediction."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-dt-b-v1", [42], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-dt-b-v1", [101], 10)

    model = DecisionTreeOutcomeModel(max_depth=5, seed=42)
    model.fit_on_dataset(train_ds)
    assert model.is_fitted

    for rec in val_ds.records:
        pred_link = model.predict(rec.model_input, RecoveryAction.PAYMENT_LINK)
        assert 0.0 <= pred_link.predicted_success_probability <= 1.0
        assert pred_link.uncertainty_state in (
            PredictionUncertaintyState.HIGH_CONFIDENCE,
            PredictionUncertaintyState.MEDIUM_CONFIDENCE,
            PredictionUncertaintyState.LOW_CONFIDENCE,
        )


def test_random_forest_outcome_model() -> None:
    """AC-12: Test Random Forest Model B training and prediction."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-rf-b-v1", [42], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-rf-b-v1", [101], 10)

    model = RandomForestOutcomeModel(n_estimators=5, max_depth=4, seed=42)
    model.fit_on_dataset(train_ds)
    assert model.is_fitted

    for rec in val_ds.records:
        pred_out = model.predict(rec.model_input, RecoveryAction.OUTREACH)
        assert 0.0 <= pred_out.predicted_success_probability <= 1.0
        assert (
            0
            <= pred_out.predicted_recovered_amount
            <= rec.model_input.features.payment_amount
        )


def test_governed_training_dataset_boundary() -> None:
    """AC-06, AC-08: Verify model fitting strictly permits TRAINING."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-gov-b-v1", [42], 20)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-gov-b-v1", [101], 10)
    test_ds = gen.generate_dataset(
        DatasetType.HELD_OUT_TEST, "test-gov-b-v1", [202], 10
    )
    bench_ds = gen.generate_dataset(DatasetType.BENCHMARK, "bench-gov-b-v1", [303], 10)

    model = LogisticRegressionOutcomeModel(max_iter=10)

    # Rejection of non-training datasets
    with pytest.raises(ValueError, match="strictly permitted on TRAINING"):
        model.fit_on_dataset(val_ds)

    with pytest.raises(ValueError, match="strictly permitted on TRAINING"):
        model.fit_on_dataset(test_ds)

    with pytest.raises(ValueError, match="strictly permitted on TRAINING"):
        model.fit_on_dataset(bench_ds)

    # Acceptance of TRAINING dataset
    model.fit_on_dataset(train_ds)
    assert model.is_fitted


def test_deterministic_prediction_identity_and_reproducibility() -> None:
    """AC-23: Verify deterministic prediction ID and 100% reproducibility."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-det-b-v1", [42], 25)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-det-b-v1", [101], 10)

    m1 = LogisticRegressionOutcomeModel(max_iter=30, seed=42)
    m1.fit_on_dataset(train_ds)

    m2 = LogisticRegressionOutcomeModel(max_iter=30, seed=42)
    m2.fit_on_dataset(train_ds)

    for rec in val_ds.records:
        for act in RecoveryAction:
            p1 = m1.predict(rec.model_input, act)
            p2 = m2.predict(rec.model_input, act)

            assert p1.predicted_success_probability == p2.predicted_success_probability
            assert p1.predicted_recovered_amount == p2.predicted_recovered_amount
            assert p1.prediction_id == p2.prediction_id
            assert p1.prediction_id.startswith("pred_rec_")
