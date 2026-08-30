"""Unit tests for probability calibration (Phase 7)."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.calibration import TemperatureCalibrator
from apro.diagnosis.classifiers import (
    MultinomialLogisticRegressionDiagnosisModel,
)
from apro.diagnosis.enums import (
    DiagnosisCategory,
)
from apro.diagnosis.labels import construct_labels_from_dataset


def test_temperature_calibrator_scaling() -> None:
    """AC-13: Test temperature scaling softens and sharpens distributions."""
    raw_probs = {
        DiagnosisCategory.TIMEOUT: 0.80,
        DiagnosisCategory.BANK_SIDE_FAILURE: 0.10,
        DiagnosisCategory.TRANSIENT_FAILURE: 0.05,
        DiagnosisCategory.AUTHENTICATION_FAILURE: 0.02,
        DiagnosisCategory.CUSTOMER_SIDE_FAILURE: 0.01,
        DiagnosisCategory.PAYMENT_METHOD_FAILURE: 0.01,
        DiagnosisCategory.GATEWAY_FAILURE: 0.005,
        DiagnosisCategory.UNKNOWN_FAILURE: 0.005,
    }

    # High temperature -> more uniform
    cal_high = TemperatureCalibrator(temperature=2.0)
    scaled_high = cal_high.calibrate(raw_probs)
    assert scaled_high[DiagnosisCategory.TIMEOUT] < 0.80
    assert abs(sum(scaled_high.values()) - 1.0) < 1e-4

    # Low temperature -> sharper
    cal_low = TemperatureCalibrator(temperature=0.5)
    scaled_low = cal_low.calibrate(raw_probs)
    assert scaled_low[DiagnosisCategory.TIMEOUT] > 0.80
    assert abs(sum(scaled_low.values()) - 1.0) < 1e-4


def test_temperature_calibrator_fitting() -> None:
    """AC-13: Test fitting temperature on validation probability outputs."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-cal-v1", [1, 2], 25)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-cal-v1", [3], 15)

    val_labels = construct_labels_from_dataset(val_ds)

    model = MultinomialLogisticRegressionDiagnosisModel(max_iter=50)
    model.fit_on_dataset(train_ds)

    # Get uncalibrated validation probabilities
    val_probs = [
        model.predict_proba_raw(model.feature_builder.transform(rec.model_input))
        for rec in val_ds.records
    ]

    calibrator = TemperatureCalibrator()
    calibrator.fit(val_probs, val_labels)

    assert calibrator.is_fitted
    assert calibrator.temperature > 0.0


def test_calibration_data_boundary() -> None:
    """Correction B: Test calibration rejects held-out and benchmark sets."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-cal-gov", [42], 25)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-cal-gov", [101], 15)
    test_ds = gen.generate_dataset(
        DatasetType.HELD_OUT_TEST, "test-cal-gov", [2026], 15
    )
    bench_ds = gen.generate_dataset(DatasetType.BENCHMARK, "bench-cal-gov", [999], 15)

    model = MultinomialLogisticRegressionDiagnosisModel(max_iter=30)
    model.fit_on_dataset(train_ds)

    calibrator = TemperatureCalibrator()

    # 1. VALIDATION is accepted
    calibrator.fit_on_dataset(model, val_ds)
    assert calibrator.is_fitted

    # 2. TRAINING is accepted
    calibrator.fit_on_dataset(model, train_ds)
    assert calibrator.is_fitted

    # 3. HELD_OUT_TEST is rejected
    with pytest.raises(
        ValueError,
        match="strictly permitted on TRAINING or VALIDATION datasets",
    ):
        calibrator.fit_on_dataset(model, test_ds)

    # 4. BENCHMARK is rejected
    with pytest.raises(
        ValueError,
        match="strictly permitted on TRAINING or VALIDATION datasets",
    ):
        calibrator.fit_on_dataset(model, bench_ds)

    # 5. fit() with explicit non-validation/training dataset_type is rejected
    val_probs = [
        model.predict_proba_raw(model.feature_builder.transform(rec.model_input))
        for rec in val_ds.records
    ]
    val_labels = construct_labels_from_dataset(val_ds)
    with pytest.raises(
        ValueError,
        match="strictly permitted on TRAINING or VALIDATION datasets",
    ):
        calibrator.fit(val_probs, val_labels, dataset_type=DatasetType.HELD_OUT_TEST)
