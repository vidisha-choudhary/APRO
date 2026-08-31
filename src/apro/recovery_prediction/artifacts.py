"""Artifact persistence, serialization, and compatibility loading for Model B."""

import json
from pathlib import Path

from apro.recovery_prediction.calibration import RecoveryTemperatureCalibrator
from apro.recovery_prediction.classifiers import (
    BaseRecoveryOutcomeModel,
    DecisionTreeOutcomeModel,
    LogisticRegressionOutcomeModel,
    RandomForestOutcomeModel,
)
from apro.recovery_prediction.enums import (
    OUTCOME_TAXONOMY_VERSION,
    RECOVERY_ACTION_SCHEMA_VERSION,
)
from apro.recovery_prediction.features import (
    RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION,
    RecoveryFeatureBuilder,
)
from apro.recovery_prediction.models import (
    RecoveryOutcomeModelArtifact,
)

ALGORITHM_REGISTRY: dict[str, type[BaseRecoveryOutcomeModel]] = {
    "LogisticRegressionOutcomeModel": LogisticRegressionOutcomeModel,
    "DecisionTreeOutcomeModel": DecisionTreeOutcomeModel,
    "RandomForestOutcomeModel": RandomForestOutcomeModel,
}


def save_recovery_model_artifact(
    model: BaseRecoveryOutcomeModel,
    target_path: str | Path,
    training_dataset_version: str = "unknown",
    training_seed: int = 42,
    created_at: str | None = None,
) -> RecoveryOutcomeModelArtifact:
    """Serialize Model B artifact to a JSON file with truthful timestamp."""
    artifact = model.to_artifact(
        training_dataset_version=training_dataset_version,
        training_seed=training_seed,
        created_at=created_at,
    )
    p = Path(target_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(artifact.model_dump(), indent=2), encoding="utf-8")
    return artifact


def load_recovery_model_artifact(
    artifact_path: str | Path,
    expected_feature_schema_version: str = RECOVERY_OUTCOME_FEATURE_SCHEMA_VERSION,
    expected_action_schema_version: str = RECOVERY_ACTION_SCHEMA_VERSION,
    expected_outcome_schema_version: str = OUTCOME_TAXONOMY_VERSION,
) -> BaseRecoveryOutcomeModel:
    """Load a Model B artifact from JSON, enforcing strict schema compatibility."""
    p = Path(artifact_path)
    if not p.exists():
        msg = f"Model artifact not found at '{artifact_path}'."
        raise FileNotFoundError(msg)

    raw_data = json.loads(p.read_text(encoding="utf-8"))
    artifact = RecoveryOutcomeModelArtifact.model_validate(raw_data)

    if artifact.feature_schema_version != expected_feature_schema_version:
        msg = (
            f"Incompatible feature schema version: artifact has "
            f"'{artifact.feature_schema_version}', "
            f"expected '{expected_feature_schema_version}'."
        )
        raise ValueError(msg)

    if artifact.action_schema_version != expected_action_schema_version:
        msg = (
            f"Incompatible action schema version: artifact has "
            f"'{artifact.action_schema_version}', "
            f"expected '{expected_action_schema_version}'."
        )
        raise ValueError(msg)

    if artifact.outcome_schema_version != expected_outcome_schema_version:
        msg = (
            f"Incompatible outcome schema version: artifact has "
            f"'{artifact.outcome_schema_version}', "
            f"expected '{expected_outcome_schema_version}'."
        )
        raise ValueError(msg)

    algo_name = artifact.algorithm
    if algo_name not in ALGORITHM_REGISTRY:
        msg = f"Unsupported algorithm '{algo_name}' in artifact."
        raise ValueError(msg)

    cls = ALGORITHM_REGISTRY[algo_name]

    # Reconstruct Feature Builder
    fb = RecoveryFeatureBuilder(
        schema_version=artifact.feature_schema_version,
        action_schema_version=artifact.action_schema_version,
    )
    if "feature_builder" in artifact.metadata:
        fb.load_dict(artifact.metadata["feature_builder"])

    # Reconstruct Calibrator
    calibrator = None
    if artifact.calibration_parameters:
        calibrator = RecoveryTemperatureCalibrator.from_dict(
            artifact.calibration_parameters
        )

    model = cls(
        model_version=artifact.model_version,
        feature_schema_version=artifact.feature_schema_version,
        action_schema_version=artifact.action_schema_version,
        outcome_schema_version=artifact.outcome_schema_version,
        feature_builder=fb,
        **artifact.hyperparameters,
    )
    model.load_parameters(artifact.parameters)
    model.calibrator = calibrator
    model._diagnosis_model_version = artifact.diagnosis_model_version
    return model
