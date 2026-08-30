"""Unit tests for diagnosis feature schema and extraction (Phase 7)."""

import pytest

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.features import (
    DIAGNOSIS_FEATURE_SCHEMA_VERSION,
    DiagnosisFeatureBuilder,
    DiagnosisFeatureVector,
)


def test_feature_builder_schema_declaration() -> None:
    """AC-04: Test feature schema version and descriptors declaration."""
    builder = DiagnosisFeatureBuilder()
    schema = builder.get_schema()

    assert schema.schema_version == DIAGNOSIS_FEATURE_SCHEMA_VERSION
    assert len(schema.feature_names) == len(builder.feature_names)
    assert len(schema.descriptors) == len(builder.feature_names)
    for desc in schema.descriptors:
        assert desc.decision_time_available is True
        assert desc.leakage_free is True


def test_feature_extraction_from_dataset() -> None:
    """AC-03, AC-04: Test extracting feature vectors strictly from ModelInputRecord."""
    gen = DatasetGenerator()
    dataset = gen.generate_dataset(DatasetType.TRAINING, "train-features-v1", [42], 15)

    builder = DiagnosisFeatureBuilder()
    vectors = builder.transform_dataset(dataset)

    assert len(vectors) == 15
    for vec, rec in zip(vectors, dataset.records, strict=True):
        assert isinstance(vec, DiagnosisFeatureVector)
        assert vec.record_id == rec.model_input.record_id
        assert len(vec.values) == len(builder.feature_names)
        # Verify amount_log10 is positive
        assert vec.values[0] > 0.0


def test_feature_builder_fitting_and_standardization() -> None:
    """AC-06: Test fitting normalization strictly on TRAINING dataset."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-norm-v1", [1, 2], 25)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-norm-v1", [3], 10)

    builder = DiagnosisFeatureBuilder()
    assert not builder.is_fitted

    # Fit on training data
    builder.fit(train_ds)
    assert builder.is_fitted

    # Transform training and validation records
    train_vecs = builder.transform_dataset(train_ds)
    val_vecs = builder.transform_dataset(val_ds)

    assert len(train_vecs) == 50
    assert len(val_vecs) == 10

    # Non-TRAINING dataset fitting must be rejected
    with pytest.raises(ValueError, match="strictly permitted on TRAINING datasets"):
        builder.fit(val_ds)
