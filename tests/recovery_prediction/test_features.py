"""Unit tests for Phase 8 recovery feature extraction and standardization."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.classifiers import DecisionTreeDiagnosisModel
from apro.recovery_prediction.enums import RecoveryAction
from apro.recovery_prediction.features import (
    RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION,
    RecoveryFeatureBuilder,
)


def test_feature_builder_schema_and_fitting() -> None:
    """AC-03, AC-04: Test feature builder extraction, fitting, and standardization."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-feat-b-v1", [42], 20)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-feat-b-v1", [101], 10)

    fb = RecoveryFeatureBuilder()
    assert not fb.is_fitted
    assert fb.schema_version == RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION

    # Unfitted transform raises ValueError
    with pytest.raises(ValueError, match="is unfitted"):
        fb.transform(val_ds.records[0].model_input, RecoveryAction.RETRY)

    # Fitting on validation dataset raises ValueError
    with pytest.raises(ValueError, match="strictly requires DatasetType.TRAINING"):
        fb.fit(val_ds)

    fb.fit(train_ds)
    assert fb.is_fitted
    assert len(fb.feature_names) > 40


def test_feature_action_sensitivity() -> None:
    """AC-03: Verify same context under different actions produces distinct vectors."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-sens-v1", [42], 15)

    fb = RecoveryFeatureBuilder()
    fb.fit(train_ds)

    rec = train_ds.records[0].model_input
    vec_retry = fb.transform(rec, RecoveryAction.RETRY)
    vec_link = fb.transform(rec, RecoveryAction.PAYMENT_LINK)
    vec_stop = fb.transform(rec, RecoveryAction.STOP)

    assert vec_retry.action == RecoveryAction.RETRY
    assert vec_link.action == RecoveryAction.PAYMENT_LINK
    assert vec_stop.action == RecoveryAction.STOP

    assert vec_retry.values != vec_link.values
    assert vec_retry.values != vec_stop.values


def test_feature_builder_with_model_a_diagnosis() -> None:
    """AC-04: Verify optional Model A diagnosis integration into feature vector."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-diag-v1", [42], 20)

    diag_model = DecisionTreeDiagnosisModel(max_depth=4)
    diag_model.fit_on_dataset(train_ds)

    fb = RecoveryFeatureBuilder()
    diag_map = {
        r.model_input.record_id: diag_model.predict(r.model_input)
        for r in train_ds.records
    }
    fb.fit(train_ds, diagnosis_results=diag_map)

    rec = train_ds.records[0].model_input
    diag_res = diag_model.predict(rec)
    vec = fb.transform(rec, RecoveryAction.RETRY, diagnosis_result=diag_res)

    assert any(name.startswith("diag_prob_") for name in vec.feature_names)
    assert any(name.startswith("act_retry_x_diag_") for name in vec.feature_names)
