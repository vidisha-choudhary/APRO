"""Unit tests for Phase 8 model artifact persistence and loading."""

from pathlib import Path

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.recovery_prediction.artifacts import (
    load_recovery_model_artifact,
    save_recovery_model_artifact,
)
from apro.recovery_prediction.classifiers import (
    DecisionTreeOutcomeModel,
    LogisticRegressionOutcomeModel,
)
from apro.recovery_prediction.enums import RecoveryAction


def test_save_and_load_recovery_artifact(tmp_path: Path) -> None:
    """AC-21, AC-22: Test artifact persistence, metadata, and reload fidelity."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-art-v1", [42], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-art-v1", [101], 10)

    model = LogisticRegressionOutcomeModel(max_iter=30, seed=42)
    model.fit_on_dataset(train_ds)

    artifact_file = tmp_path / "model_b_test.json"
    artifact = save_recovery_model_artifact(
        model,
        artifact_file,
        training_dataset_version="train-art-v1",
        training_seed=42,
    )

    assert artifact.model_name == "Logistic Regression Outcome Model"
    assert artifact.deterministic_identity is not None
    assert artifact_file.exists()

    reloaded_model = load_recovery_model_artifact(artifact_file)
    assert reloaded_model.is_fitted
    assert reloaded_model.model_name == model.model_name
    assert reloaded_model.model_version == model.model_version

    for rec in val_ds.records:
        for act in (RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK):
            p1 = model.predict(rec.model_input, act)
            p2 = reloaded_model.predict(rec.model_input, act)
            assert p1.predicted_success_probability == p2.predicted_success_probability
            assert p1.predicted_recovered_amount == p2.predicted_recovered_amount
            assert p1.prediction_id == p2.prediction_id


def test_artifact_deterministic_identity_vs_creation_timestamp() -> None:
    """AC-21: Verify created_at records actual time while identity is invariant."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-id-b-v1", [42], 25)

    model = DecisionTreeOutcomeModel(max_depth=5, seed=42)
    model.fit_on_dataset(train_ds)

    art1 = model.to_artifact(
        training_dataset_version="train-id-b-v1",
        training_seed=42,
        created_at="2026-08-31T10:00:00Z",
    )
    art2 = model.to_artifact(
        training_dataset_version="train-id-b-v1",
        training_seed=42,
        created_at="2026-08-31T12:00:00Z",
    )

    assert art1.created_at != art2.created_at
    assert art1.deterministic_identity == art2.deterministic_identity


def test_incompatible_schema_rejection(tmp_path: Path) -> None:
    """AC-22: Verify rejection of incompatible schema versions on load."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-incomp-v1", [42], 20)

    model = LogisticRegressionOutcomeModel(max_iter=10)
    model.fit_on_dataset(train_ds)

    artifact_file = tmp_path / "model_b_bad_schema.json"
    save_recovery_model_artifact(model, artifact_file)

    with pytest.raises(ValueError, match="Incompatible feature schema version"):
        load_recovery_model_artifact(
            artifact_file,
            expected_feature_schema_version="incompatible-feature-v99",
        )

    with pytest.raises(ValueError, match="Incompatible action schema version"):
        load_recovery_model_artifact(
            artifact_file,
            expected_action_schema_version="incompatible-action-v99",
        )
