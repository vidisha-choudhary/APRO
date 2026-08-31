"""Unit tests for Phase 8 supervised outcome label construction."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.recovery_prediction.enums import (
    PredictedOutcomeState,
    RecoveryAction,
)
from apro.recovery_prediction.labels import (
    construct_outcome_label,
    construct_outcome_labels_from_dataset,
)


def test_construct_outcome_labels_from_dataset() -> None:
    """AC-02: Test constructing action-conditioned labels from GovernedDataset."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-labels-v1", [42], 10)

    labels = construct_outcome_labels_from_dataset(train_ds)
    # 10 records * 5 actions = 50 labels
    assert len(labels) == 50

    for lbl in labels:
        assert lbl.outcome_state in (
            PredictedOutcomeState.SUCCESS,
            PredictedOutcomeState.FAILURE,
            PredictedOutcomeState.PENDING,
        )
        assert lbl.recovered_amount >= 0
        if lbl.outcome_state == PredictedOutcomeState.SUCCESS:
            assert lbl.recovered_amount > 0
        elif lbl.outcome_state == PredictedOutcomeState.FAILURE:
            assert lbl.recovered_amount == 0


def test_construct_single_outcome_label_mapping() -> None:
    """AC-02: Verify exact mapping of simulator truth to RecoveryOutcomeLabel."""
    gen = DatasetGenerator()
    ds = gen.generate_dataset(DatasetType.TRAINING, "test-single-v1", [101], 1)
    rec = ds.records[0]

    for act in RecoveryAction:
        lbl = construct_outcome_label(
            truth_record=rec.evaluation_truth,
            action=act,
            payment_amount=rec.model_input.features.payment_amount,
            dataset_version=ds.manifest.dataset_version,
        )
        assert lbl.action == act
        assert lbl.scenario_id == rec.model_input.scenario_id
