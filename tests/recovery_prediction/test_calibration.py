"""Unit tests for Phase 8 recovery outcome probability calibration."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.recovery_prediction.calibration import (
    RecoveryTemperatureCalibrator,
)
from apro.recovery_prediction.classifiers import (
    LogisticRegressionOutcomeModel,
)
from apro.recovery_prediction.enums import (
    OUTCOME_TAXONOMY_VERSION,
    RECOVERY_ACTION_SCHEMA_VERSION,
    PredictedOutcomeState,
    RecoveryAction,
)
from apro.recovery_prediction.models import RecoveryOutcomeLabel


def test_temperature_calibrator_scaling() -> None:
    """AC-14: Test temperature scaling softens and sharpens distributions."""
    cal = RecoveryTemperatureCalibrator(
        temperatures={
            RecoveryAction.RETRY: 2.0,
            RecoveryAction.PAYMENT_LINK: 0.5,
        }
    )

    # STOP is always 0.0
    assert cal.calibrate_probability(0.8, RecoveryAction.STOP) == 0.0

    # Temperature > 1 softens extreme probability toward 0.5
    raw_high = 0.90
    cal_soft = cal.calibrate_probability(raw_high, RecoveryAction.RETRY)
    assert 0.5 < cal_soft < raw_high

    # Temperature < 1 sharpens probability toward 1.0
    cal_sharp = cal.calibrate_probability(raw_high, RecoveryAction.PAYMENT_LINK)
    assert cal_sharp > raw_high


def test_calibrator_fitting_and_governance() -> None:
    """AC-07, AC-08, AC-14: Test calibrator fitting permissions."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-cal-b-v1", [42], 25)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-cal-b-v1", [101], 15)
    test_ds = gen.generate_dataset(
        DatasetType.HELD_OUT_TEST, "test-cal-b-v1", [202], 10
    )

    model = LogisticRegressionOutcomeModel(max_iter=20)
    model.fit_on_dataset(train_ds)

    cal = RecoveryTemperatureCalibrator()
    assert not cal.is_fitted

    # Fitting on VALIDATION is permitted
    cal.fit_on_dataset(model, val_ds)
    assert cal.is_fitted
    assert len(cal.temperatures) == 5

    # Fitting on TRAINING is permitted
    cal.fit_on_dataset(model, train_ds)
    assert cal.is_fitted

    # Fitting on HELD_OUT_TEST is strictly forbidden
    with pytest.raises(
        ValueError, match="strictly permitted on TRAINING or VALIDATION"
    ):
        cal.fit_on_dataset(model, test_ds)


def test_calibrator_with_synthetic_labels() -> None:
    """Test manual calibrator fitting with known probability arrays."""
    cal = RecoveryTemperatureCalibrator()

    probs = {
        RecoveryAction.RETRY: [0.9, 0.8, 0.85, 0.75, 0.9],
        RecoveryAction.PAYMENT_LINK: [0.1, 0.2, 0.15, 0.05, 0.2],
        RecoveryAction.OUTREACH: [0.5, 0.5, 0.5, 0.5, 0.5],
        RecoveryAction.STOP: [0.0, 0.0, 0.0, 0.0, 0.0],
        RecoveryAction.ESCALATE: [0.0, 0.0, 0.0, 0.0, 0.0],
    }

    labels = {
        RecoveryAction.RETRY: [
            RecoveryOutcomeLabel(
                record_id=f"r{i}",
                scenario_id=f"s{i}",
                action=RecoveryAction.RETRY,
                outcome_state=PredictedOutcomeState.SUCCESS,
                recovered_amount=1000,
                dataset_version="d1",
                action_schema_version=RECOVERY_ACTION_SCHEMA_VERSION,
                outcome_schema_version=OUTCOME_TAXONOMY_VERSION,
            )
            for i in range(5)
        ],
        RecoveryAction.PAYMENT_LINK: [
            RecoveryOutcomeLabel(
                record_id=f"r{i}",
                scenario_id=f"s{i}",
                action=RecoveryAction.PAYMENT_LINK,
                outcome_state=PredictedOutcomeState.FAILURE,
                recovered_amount=0,
                dataset_version="d1",
                action_schema_version=RECOVERY_ACTION_SCHEMA_VERSION,
                outcome_schema_version=OUTCOME_TAXONOMY_VERSION,
            )
            for i in range(5)
        ],
    }

    cal.fit(probs, labels, dataset_type=DatasetType.VALIDATION)
    assert cal.is_fitted
    assert cal.temperatures[RecoveryAction.RETRY] > 0.0
