"""Unit tests for diagnosis label construction (Phase 7)."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_VERSION,
    DiagnosisCategory,
)
from apro.diagnosis.labels import (
    construct_diagnosis_label,
    construct_labels_from_dataset,
)
from apro.simulation.enums import ScenarioFamily


def test_construct_diagnosis_label_mapping() -> None:
    """AC-02: Test constructing DiagnosisLabel from EvaluationTruthRecord."""
    gen = DatasetGenerator()
    dataset = gen.generate_dataset(DatasetType.TRAINING, "train-labels-v1", [42], 10)

    for rec in dataset.records:
        lbl = construct_diagnosis_label(rec.evaluation_truth)
        assert lbl.record_id == rec.model_input.record_id
        assert lbl.scenario_id == rec.model_input.scenario_id
        assert lbl.taxonomy_version == DIAGNOSIS_TAXONOMY_VERSION
        assert lbl.label_source == "governed_simulator_ground_truth"
        assert isinstance(lbl.failure_category, DiagnosisCategory)


def test_construct_labels_from_dataset() -> None:
    """AC-02: Test batch label construction for an entire GovernedDataset."""
    gen = DatasetGenerator()
    dataset = gen.generate_dataset(DatasetType.TRAINING, "train-batch-v1", [101], 25)

    labels = construct_labels_from_dataset(dataset)
    assert len(labels) == 25
    for lbl, rec in zip(labels, dataset.records, strict=True):
        assert lbl.record_id == rec.model_input.record_id
        assert (
            lbl.failure_category.value
            == ScenarioFamily(rec.evaluation_truth.scenario_family).value
        )
