"""Unit tests for diagnosis baseline models (Phase 7)."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.baselines import (
    HistoricalConditionalBaseline,
    MajorityClassBaseline,
    NaiveBayesDiagnosisModel,
    ProviderRuleBaseline,
)
from apro.diagnosis.enums import (
    DiagnosisCategory,
)


def test_majority_class_baseline() -> None:
    """AC-09: Test Majority Class Baseline predictions and probability distributions."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-maj-v1", [42], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-maj-v1", [101], 10)

    model = MajorityClassBaseline()
    assert not model.is_fitted

    model.fit_on_dataset(train_ds)
    assert model.is_fitted

    for rec in val_ds.records:
        res = model.predict(rec.model_input)
        assert isinstance(res.predicted_category, DiagnosisCategory)
        assert res.confidence > 0.0
        assert len(res.class_probabilities) == 8


def test_provider_rule_baseline() -> None:
    """AC-09: Test Provider Rule Baseline deterministic code mappings."""
    model = ProviderRuleBaseline()
    assert model.is_fitted

    gen = DatasetGenerator()
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-rules-v1", [42], 10)

    for rec in val_ds.records:
        res = model.predict(rec.model_input)
        assert isinstance(res.predicted_category, DiagnosisCategory)
        assert len(res.class_probabilities) == 8
        assert res.confidence >= 0.80


def test_historical_conditional_baseline() -> None:
    """AC-09: Test Historical Conditional Baseline fitting and predictions."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-hist-v1", [1, 2], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-hist-v1", [3], 10)

    model = HistoricalConditionalBaseline()
    model.fit_on_dataset(train_ds)

    for rec in val_ds.records:
        res = model.predict(rec.model_input)
        assert isinstance(res.predicted_category, DiagnosisCategory)
        assert len(res.class_probabilities) == 8


def test_naive_bayes_diagnosis_model() -> None:
    """AC-09: Test Naive Bayes baseline classifier."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-nb-v1", [10, 20], 30)
    val_ds = gen.generate_dataset(DatasetType.VALIDATION, "val-nb-v1", [30], 10)

    model = NaiveBayesDiagnosisModel()
    model.fit_on_dataset(train_ds)

    for rec in val_ds.records:
        res = model.predict(rec.model_input)
        assert isinstance(res.predicted_category, DiagnosisCategory)
        assert len(res.class_probabilities) == 8
