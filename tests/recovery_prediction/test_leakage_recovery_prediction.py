"""Information leakage prevention tests for Phase 8 Recovery Prediction."""

from apro.dataset.enums import DatasetType
from apro.dataset.generator import DatasetGenerator
from apro.dataset.models import DatasetRecord
from apro.recovery_prediction.enums import RecoveryAction
from apro.recovery_prediction.features import RecoveryFeatureBuilder
from apro.simulation.enums import (
    ScenarioFamily,
    SimulatedActionType,
    SimulatedOutcomeStatus,
)


def test_features_isolated_from_hidden_simulator_truth() -> None:
    """AC-05: Verify Model B feature vector is isolated from simulator truth."""
    gen = DatasetGenerator()
    train_ds = gen.generate_dataset(DatasetType.TRAINING, "train-leak-b-v1", [42], 20)

    fb = RecoveryFeatureBuilder()
    fb.fit(train_ds)

    rec = train_ds.records[0]
    base_feat = fb.transform(rec.model_input, RecoveryAction.RETRY)

    # DatasetRecord with identical model_input but altered evaluation_truth
    tampered_truth = rec.evaluation_truth.model_copy(
        update={
            "scenario_family": ScenarioFamily.GATEWAY_FAILURE,
            "best_achievable_action": SimulatedActionType.STOP,
            "best_achievable_value": 0,
            "potential_outcomes": dict.fromkeys(
                SimulatedActionType, SimulatedOutcomeStatus.FAILURE
            ),
        }
    )
    tampered_rec = DatasetRecord(
        model_input=rec.model_input,
        evaluation_truth=tampered_truth,
    )

    # Feature extraction MUST produce an identical feature vector
    tampered_feat = fb.transform(tampered_rec.model_input, RecoveryAction.RETRY)

    assert base_feat.values == tampered_feat.values
    assert base_feat.feature_names == tampered_feat.feature_names
