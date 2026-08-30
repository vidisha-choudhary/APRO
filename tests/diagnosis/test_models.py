"""Unit tests for Model A candidate classifiers (Phase 7)."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.classifiers import (
    DecisionTreeDiagnosisModel,
    MultinomialLogisticRegressionDiagnosisModel,
    RandomForestDiagnosisModel,
)
from apro.diagnosis.enums import (
    DiagnosisCategory,
)


def test_logistic_regression_diagnosis_model() -> None:
    """AC-10, AC-11: Test Multinomial Logistic Regression Model training."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-lr-v1", [42, 101], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-lr-v1", [2026], 10)

    model = MultinomialLogisticRegressionDiagnosisModel(
        max_iter=100, learning_rate=0.05
    )
    assert not model.is_fitted

    # Unfitted predict raises ValueError
    with pytest.raises(ValueError, match="is unfitted"):
        model.predict(val_ds.records[0].model_input)

    model.fit_on_dataset(train_ds)
    assert model.is_fitted

    for rec in val_ds.records:
        res = model.predict(rec.model_input)
        assert isinstance(res.predicted_category, DiagnosisCategory)
        assert len(res.class_probabilities) == 8
        assert res.confidence > 0.0
        assert abs(sum(res.class_probabilities.values()) - 1.0) < 1e-4


def test_decision_tree_diagnosis_model() -> None:
    """AC-10, AC-11: Test Decision Tree Model training and prediction."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-dt-v1", [42], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-dt-v1", [101], 10)

    model = DecisionTreeDiagnosisModel(max_depth=5)
    assert not model.is_fitted

    model.fit_on_dataset(train_ds)
    assert model.is_fitted

    for rec in val_ds.records:
        res = model.predict(rec.model_input)
        assert isinstance(res.predicted_category, DiagnosisCategory)
        assert len(res.class_probabilities) == 8
        assert abs(sum(res.class_probabilities.values()) - 1.0) < 1e-4


def test_random_forest_diagnosis_model() -> None:
    """AC-10, AC-11: Test Random Forest Model training and prediction."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-rf-v1", [42], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-rf-v1", [101], 10)

    model = RandomForestDiagnosisModel(n_estimators=5, max_depth=5)
    assert not model.is_fitted

    model.fit_on_dataset(train_ds)
    assert model.is_fitted

    for rec in val_ds.records:
        res = model.predict(rec.model_input)
        assert isinstance(res.predicted_category, DiagnosisCategory)
        assert len(res.class_probabilities) == 8
        assert abs(sum(res.class_probabilities.values()) - 1.0) < 1e-4


def test_governed_training_dataset_boundary() -> None:
    """Correction 1: Verify model fitting strictly requires DatasetType.TRAINING."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-gov-v1", [42], 20)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-gov-v1", [101], 10)
    test_ds = gen.generate_dataset(DatasetType.HELD_OUT_TEST, "test-gov-v1", [2026], 10)
    bench_ds = gen.generate_dataset(DatasetType.BENCHMARK, "bench-gov-v1", [999], 10)

    model = DecisionTreeDiagnosisModel(max_depth=4)

    # 1. TRAINING dataset is accepted
    model.fit_on_dataset(train_ds)
    assert model.is_fitted

    # 2. VALIDATION dataset is rejected
    with pytest.raises(ValueError, match="strictly permitted on TRAINING datasets"):
        model.fit_on_dataset(val_ds)

    # 3. HELD_OUT_TEST dataset is rejected
    with pytest.raises(ValueError, match="strictly permitted on TRAINING datasets"):
        model.fit_on_dataset(test_ds)

    # 4. BENCHMARK dataset is rejected
    with pytest.raises(ValueError, match="strictly permitted on TRAINING datasets"):
        model.fit_on_dataset(bench_ds)


def test_deterministic_prediction_identity_and_reproducibility() -> None:
    """Correction C: Verify deterministic prediction ID & reproducibility."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-det-v1", [42], 25)
    test_ds = gen.generate_dataset(DatasetType.HELD_OUT_TEST, "test-det-v1", [101], 5)

    model = DecisionTreeDiagnosisModel(max_depth=5)
    model.fit_on_dataset(train_ds)

    input_rec = test_ds.records[0].model_input

    # Repeated prediction calls on same model and input
    res1 = model.predict(input_rec)
    res2 = model.predict(input_rec)

    # Full dictionary representation must match bit-for-bit
    assert res1.model_dump() == res2.model_dump()
    assert res1.prediction_id == res2.prediction_id
    assert res1.predicted_category == res2.predicted_category
    assert res1.confidence == res2.confidence
    assert res1.uncertainty_state == res2.uncertainty_state
    assert res1.class_probabilities == res2.class_probabilities

    # Different input record produces different deterministic prediction_id
    input_rec2 = test_ds.records[1].model_input
    res3 = model.predict(input_rec2)
    assert res1.prediction_id != res3.prediction_id
