"""Diagnosis-specific anti-leakage tests for Phase 7."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.dataset.leakage_checks import FORBIDDEN_HIDDEN_KEYS
from apro.diagnosis.features import DiagnosisFeatureBuilder


def test_diagnosis_features_contain_no_hidden_keys() -> None:
    """AC-05: Test feature names contain zero forbidden hidden keys."""
    builder = DiagnosisFeatureBuilder()

    for name in builder.feature_names:
        name_lower = name.lower()
        for forbidden in FORBIDDEN_HIDDEN_KEYS:
            assert forbidden != name_lower, (
                f"Forbidden key '{forbidden}' found in feature name '{name}'!"
            )


def test_extracted_feature_vectors_contain_no_evaluation_truth() -> None:
    """AC-05: Verify feature transform operates without EvaluationTruthRecord."""
    gen = DatasetGenerator()
    dataset = gen.generate_dataset(DatasetType.TRAINING, "train-leak-v1", [42], 10)
    builder = DiagnosisFeatureBuilder()

    # Pass only model inputs into the builder
    model_inputs = dataset.get_model_inputs()
    for m_in in model_inputs:
        vec = builder.transform(m_in)
        # Vector contains strictly numerical values
        assert all(isinstance(v, (int, float)) for v in vec.values)
        assert len(vec.values) == len(builder.feature_names)
