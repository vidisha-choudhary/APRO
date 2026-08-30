import json
import tempfile
from pathlib import Path

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.artifacts import (
    load_model_artifact,
    save_model_artifact,
)
from apro.diagnosis.classifiers import (
    DecisionTreeDiagnosisModel,
    MultinomialLogisticRegressionDiagnosisModel,
)


def test_save_and_load_logistic_regression_artifact() -> None:
    """AC-18, AC-23: Test saving and loading Logistic Regression model artifact."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-art-v1", [42], 25)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-art-v1", [101], 5)

    model = MultinomialLogisticRegressionDiagnosisModel(max_iter=30)
    model.fit_on_dataset(train_ds)

    with tempfile.TemporaryDirectory() as tmpdir:
        art_path = Path(tmpdir) / "model_a.json"
        artifact = save_model_artifact(
            model,
            art_path,
            training_dataset_version="train-art-v1",
            training_seed=42,
        )

        assert art_path.exists()
        assert artifact.created_at is not None
        assert artifact.deterministic_identity is not None

        loaded_model = load_model_artifact(art_path)

        assert loaded_model.model_name == model.model_name
        assert loaded_model.is_fitted

        # Verify predictions match identically bit-for-bit
        for rec in val_ds.records:
            orig_res = model.predict(rec.model_input)
            loaded_res = loaded_model.predict(rec.model_input)

            assert orig_res.model_dump() == loaded_res.model_dump()
            assert orig_res.prediction_id == loaded_res.prediction_id
            assert orig_res.predicted_category == loaded_res.predicted_category
            assert orig_res.confidence == loaded_res.confidence
            assert orig_res.class_probabilities == loaded_res.class_probabilities


def test_artifact_created_at_and_deterministic_identity() -> None:
    """Correction 2: Test truthful created_at separation from deterministic identity."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-ident-v1", [42], 20)

    model = DecisionTreeDiagnosisModel(max_depth=4)
    model.fit_on_dataset(train_ds)

    # Artifact 1 created at time T1
    art1 = model.to_artifact(
        training_dataset_version="train-ident-v1",
        created_at="2026-08-31T01:00:00+00:00",
    )

    # Artifact 2 created at time T2
    art2 = model.to_artifact(
        training_dataset_version="train-ident-v1",
        created_at="2026-08-31T02:00:00+00:00",
    )

    # Creation timestamps must be different
    assert art1.created_at != art2.created_at

    # Deterministic fingerprints must be identical
    assert art1.deterministic_identity == art2.deterministic_identity
    assert (
        art1.compute_deterministic_identity() == art2.compute_deterministic_identity()
    )


def test_incompatible_artifact_rejection() -> None:
    """AC-23: Test loading incompatible schema or taxonomy version raises ValueError."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-compat-v1", [1], 15)

    model = DecisionTreeDiagnosisModel(max_depth=3)
    model.fit_on_dataset(train_ds)

    with tempfile.TemporaryDirectory() as tmpdir:
        art_path = Path(tmpdir) / "model_tree.json"
        save_model_artifact(model, art_path)

        # Mutate schema version
        raw = json.loads(art_path.read_text(encoding="utf-8"))
        raw["feature_schema_version"] = "incompatible-schema-v99"
        art_path.write_text(json.dumps(raw), encoding="utf-8")

        with pytest.raises(ValueError, match="Incompatible feature schema version"):
            load_model_artifact(art_path)
